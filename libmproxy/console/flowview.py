# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, sys
import urwid
import common, grideditor, contentview
from .. import utils, flow

def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("b", "save request/response body"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("e", "edit request/response"),
        ("f", "load full body data"),
        ("m", "change body display mode for this entity"),
            (None,
                common.highlight_key("automatic", "a") +
                [("text", ": automatic detection")]
            ),
            (None,
                common.highlight_key("hex", "e") +
                [("text", ": Hex")]
            ),
            (None,
                common.highlight_key("html", "h") +
                [("text", ": HTML")]
            ),
            (None,
                common.highlight_key("image", "i") +
                [("text", ": Image")]
            ),
            (None,
                common.highlight_key("javascript", "j") +
                [("text", ": JavaScript")]
            ),
            (None,
                common.highlight_key("json", "s") +
                [("text", ": JSON")]
            ),
            (None,
                common.highlight_key("urlencoded", "u") +
                [("text", ": URL-encoded data")]
            ),
            (None,
                common.highlight_key("raw", "r") +
                [("text", ": raw data")]
            ),
            (None,
                common.highlight_key("xml", "x") +
                [("text", ": XML")]
            ),
        ("M", "change default body display mode"),
        ("p", "previous flow"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("v", "view body in external viewer"),
        ("w", "save all flows matching current limit"),
        ("W", "save this flow"),
        ("x", "delete body"),
        ("X", "view flow details"),
        ("z", "encode/decode a request/response"),
        ("tab", "toggle request/response view"),
        ("space", "next flow"),
        ("|", "run script on this flow"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()

footer = [
    ('heading_key', "?"), ":help ",
    ('heading_key', "q"), ":back ",
]


class FlowViewHeader(common.WWrap):
    def __init__(self, master, f):
        self.master, self.flow = master, f
        self.w = common.format_flow(f, False, extended=True, padding=0, hostheader=self.master.showhost)

    def refresh_flow(self, f):
        if f == self.flow:
            self.w = common.format_flow(f, False, extended=True, padding=0, hostheader=self.master.showhost)


class CallbackCache:
    @utils.LRUCache(200)
    def _callback(self, method, *args, **kwargs):
        return getattr(self.obj, method)(*args, **kwargs)

    def callback(self, obj, method, *args, **kwargs):
        # obj varies!
        self.obj = obj
        return self._callback(method, *args, **kwargs)
cache = CallbackCache()


class FlowView(common.WWrap):
    REQ = 0
    RESP = 1
    method_options = [
        ("get", "g"),
        ("post", "p"),
        ("put", "u"),
        ("head", "h"),
        ("trace", "t"),
        ("delete", "d"),
        ("options", "o"),
        ("edit raw", "e"),
    ]
    def __init__(self, master, state, flow):
        self.master, self.state, self.flow = master, state, flow
        if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.view_response()
        else:
            self.view_request()

    def _cached_content_view(self, viewmode, hdrItems, content, limit):
        return contentview.get_content_view(viewmode, hdrItems, content, limit, self.master.add_event)

    def content_view(self, viewmode, conn):
        full = self.state.get_flow_setting(
            self.flow,
            (self.state.view_flow_mode, "fullcontents"),
            False
        )
        if full:
            limit = sys.maxint
        else:
            limit = contentview.VIEW_CUTOFF
        return cache.callback(
                    self, "_cached_content_view",
                    viewmode,
                    tuple(tuple(i) for i in conn.headers.lst),
                    conn.content,
                    limit
                )

    def conn_text(self, conn):
        txt = common.format_keyvals(
                [(h+":", v) for (h, v) in conn.headers.lst],
                key = "header",
                val = "text"
            )
        if conn.content is not None:
            override = self.state.get_flow_setting(
                self.flow,
                (self.state.view_flow_mode, "prettyview"),
            )
            viewmode = self.state.default_body_view if override is None else override

            if conn.content == flow.CONTENT_MISSING:
                msg, body = "", [urwid.Text([("error", "[content missing]")])]
            else:
                msg, body = self.content_view(viewmode, conn)

            cols = [
                urwid.Text(
                    [
                        ("heading", msg),
                    ]
                )
            ]
            if override is not None:
                cols.append(
                    urwid.Text(
                        [
                            " ",
                            ('heading', "["),
                            ('heading_key', "m"),
                            ('heading', (":%s]"%viewmode.name)),
                        ],
                        align="right"
                    )
                )
            title = urwid.AttrWrap(urwid.Columns(cols), "heading")
            txt.append(title)
            txt.extend(body)
        elif conn.content == flow.CONTENT_MISSING:
            pass
        return urwid.ListBox(txt)

    def _tab(self, content, attr):
        p = urwid.Text(content)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, attr)
        return p

    def wrap_body(self, active, body):
        parts = []

        if self.flow.intercepting and not self.flow.request.reply.acked:
            qt = "Request intercepted"
        else:
            qt = "Request"
        if active == common.VIEW_FLOW_REQUEST:
            parts.append(self._tab(qt, "heading"))
        else:
            parts.append(self._tab(qt, "heading_inactive"))

        if self.flow.intercepting and self.flow.response and not self.flow.response.reply.acked:
            st = "Response intercepted"
        else:
            st = "Response"
        if active == common.VIEW_FLOW_RESPONSE:
            parts.append(self._tab(st, "heading"))
        else:
            parts.append(self._tab(st, "heading_inactive"))

        h = urwid.Columns(parts)
        f = urwid.Frame(
                    body,
                    header=h
                )
        return f

    def view_request(self):
        self.state.view_flow_mode = common.VIEW_FLOW_REQUEST
        body = self.conn_text(self.flow.request)
        self.w = self.wrap_body(common.VIEW_FLOW_REQUEST, body)
        self.master.statusbar.redraw()

    def view_response(self):
        self.state.view_flow_mode = common.VIEW_FLOW_RESPONSE
        if self.flow.response:
            body = self.conn_text(self.flow.response)
        else:
            body = urwid.ListBox(
                        [
                            urwid.Text(""),
                            urwid.Text(
                                [
                                    ("highlight", "No response. Press "),
                                    ("key", "e"),
                                    ("highlight", " and edit any aspect to add one."),
                                ]
                            )
                        ]
                   )
        self.w = self.wrap_body(common.VIEW_FLOW_RESPONSE, body)
        self.master.statusbar.redraw()

    def refresh_flow(self, c=None):
        if c == self.flow:
            if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE and self.flow.response:
                self.view_response()
            else:
                self.view_request()

    def set_method_raw(self, m):
        if m:
            self.flow.request.method = m
            self.master.refresh_flow(self.flow)

    def edit_method(self, m):
        if m == "e":
            self.master.prompt_edit("Method", self.flow.request.method, self.set_method_raw)
        else:
            for i in self.method_options:
                if i[1] == m:
                    self.flow.request.method = i[0].upper()
            self.master.refresh_flow(self.flow)

    def save_body(self, path):
        if not path:
            return
        self.state.last_saveload = path
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            c = self.flow.request
        else:
            c = self.flow.response
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            f.write(str(c.content))
            f.close()
        except IOError, v:
            self.master.statusbar.message(v.strerror)

    def set_url(self, url):
        request = self.flow.request
        if not request.set_url(str(url)):
            return "Invalid URL."
        self.master.refresh_flow(self.flow)

    def set_resp_code(self, code):
        response = self.flow.response
        try:
            response.code = int(code)
        except ValueError:
            return None
        import BaseHTTPServer
        if BaseHTTPServer.BaseHTTPRequestHandler.responses.has_key(int(code)):
            response.msg = BaseHTTPServer.BaseHTTPRequestHandler.responses[int(code)][0]
        self.master.refresh_flow(self.flow)

    def set_resp_msg(self, msg):
        response = self.flow.response
        response.msg = msg
        self.master.refresh_flow(self.flow)

    def set_headers(self, lst, conn):
        conn.headers = flow.ODictCaseless(lst)

    def set_query(self, lst, conn):
        conn.set_query(flow.ODict(lst))

    def set_path_components(self, lst, conn):
        conn.set_path_components([i[0] for i in lst])

    def set_form(self, lst, conn):
        conn.set_form_urlencoded(flow.ODict(lst))

    def edit_form(self, conn):
        self.master.view_grideditor(
            grideditor.URLEncodedFormEditor(self.master, conn.get_form_urlencoded().lst, self.set_form, conn)
        )

    def edit_form_confirm(self, key, conn):
        if key == "y":
            self.edit_form(conn)

    def edit(self, part):
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            if not self.flow.response:
                self.flow.response = flow.Response(self.flow.request, 200, "OK", flow.ODictCaseless(), "", None)
            conn = self.flow.response

        self.flow.backup()
        if part == "r":
            c = self.master.spawn_editor(conn.content or "")
            conn.content = c.rstrip("\n") # what?
        elif part == "f":
            if not conn.get_form_urlencoded() and conn.content:
                self.master.prompt_onekey(
                    "Existing body is not a URL-encoded form. Clear and edit?",
                    [
                        ("yes", "y"),
                        ("no", "n"),
                    ],
                    self.edit_form_confirm,
                    conn
                )
            else:
                self.edit_form(conn)
        elif part == "h":
            self.master.view_grideditor(grideditor.HeaderEditor(self.master, conn.headers.lst, self.set_headers, conn))
        elif part == "p":
            p = conn.get_path_components()
            p = [[i] for i in p]
            self.master.view_grideditor(grideditor.PathEditor(self.master, p, self.set_path_components, conn))
        elif part == "q":
            self.master.view_grideditor(grideditor.QueryEditor(self.master, conn.get_query().lst, self.set_query, conn))
        elif part == "u" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_edit("URL", conn.get_url(), self.set_url)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_onekey("Method", self.method_options, self.edit_method)
        elif part == "c" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Code", str(conn.code), self.set_resp_code)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Message", conn.msg, self.set_resp_msg)
        self.master.refresh_flow(self.flow)

    def _view_nextprev_flow(self, np, flow):
        try:
            idx = self.state.view.index(flow)
        except IndexError:
            return
        if np == "next":
            new_flow, new_idx = self.state.get_next(idx)
        else:
            new_flow, new_idx = self.state.get_prev(idx)
        if new_idx is None:
            self.master.statusbar.message("No more flows!")
            return
        self.master.view_flow(new_flow)

    def view_next_flow(self, flow):
        return self._view_nextprev_flow("next", flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow("prev", flow)

    def change_this_display_mode(self, t):
        self.state.add_flow_setting(
            self.flow,
            (self.state.view_flow_mode, "prettyview"),
            contentview.get_by_shortcut(t)
        )
        self.master.refresh_flow(self.flow)

    def delete_body(self, t):
        if t == "m":
            val = flow.CONTENT_MISSING
        else:
            val = None
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.flow.request.content = val
        else:
            self.flow.response.content = val
        self.master.refresh_flow(self.flow)

    def keypress(self, size, key):
        if key == " ":
            self.view_next_flow(self.flow)
            return

        key = common.shortcuts(key)
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            conn = self.flow.response

        if key == "q":
            self.master.view_flowlist()
            key = None
        elif key == "tab":
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                self.view_response()
            else:
                self.view_request()
        elif key in ("up", "down", "page up", "page down"):
            # Why doesn't this just work??
            self.w.keypress(size, key)
        elif key == "a":
            self.flow.accept_intercept()
            self.master.view_flow(self.flow)
        elif key == "A":
            self.master.accept_all()
            self.master.view_flow(self.flow)
        elif key == "b":
            if conn:
                if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                    self.master.path_prompt(
                        "Save request body: ",
                        self.state.last_saveload,
                        self.save_body
                    )
                else:
                    self.master.path_prompt(
                        "Save response body: ",
                        self.state.last_saveload,
                        self.save_body
                    )
        elif key == "d":
            if self.state.flow_count() == 1:
                self.master.view_flowlist()
            elif self.state.view.index(self.flow) == len(self.state.view)-1:
                self.view_prev_flow(self.flow)
            else:
                self.view_next_flow(self.flow)
            f = self.flow
            f.kill(self.master)
            self.state.delete_flow(f)
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.view_flow(f)
            self.master.currentflow = f
            self.master.statusbar.message("Duplicated.")
        elif key == "e":
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                self.master.prompt_onekey(
                    "Edit request",
                    (
                        ("query", "q"),
                        ("path", "p"),
                        ("url", "u"),
                        ("header", "h"),
                        ("form", "f"),
                        ("raw body", "r"),
                        ("method", "m"),
                    ),
                    self.edit
                )
            else:
                self.master.prompt_onekey(
                    "Edit response",
                    (
                        ("code", "c"),
                        ("message", "m"),
                        ("header", "h"),
                        ("raw body", "r"),
                    ),
                    self.edit
                )
            key = None
        elif key == "f":
            self.master.statusbar.message("Loading all body data...")
            self.state.add_flow_setting(
                self.flow,
                (self.state.view_flow_mode, "fullcontents"),
                True
            )
            self.master.refresh_flow(self.flow)
            self.master.statusbar.message("")
        elif key == "m":
            p = list(contentview.view_prompts)
            p.insert(0, ("clear", "c"))
            self.master.prompt_onekey(
                "Display mode",
                p,
                self.change_this_display_mode
            )
            key = None
        elif key == "p":
            self.view_prev_flow(self.flow)
        elif key == "r":
            self.flow.backup()
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.refresh_flow(self.flow)
        elif key == "V":
            if not self.flow.modified():
                self.master.statusbar.message("Flow not modified.")
                return
            self.state.revert(self.flow)
            self.master.refresh_flow(self.flow)
            self.master.statusbar.message("Reverted.")
        elif key == "W":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "v":
            if conn and conn.content:
                t = conn.headers["content-type"] or [None]
                t = t[0]
                if os.environ.has_key("EDITOR") or os.environ.has_key("PAGER"):
                    self.master.spawn_external_viewer(conn.content, t)
                else:
                    self.master.statusbar.message("Error! Set $EDITOR or $PAGER.")
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ", self.state.last_script,
                self.master.run_script_once, self.flow
            )
        elif key == "x":
            self.master.prompt_onekey(
                "Delete body",
                (
                    ("completely", "c"),
                    ("mark as missing", "m"),
                ),
                self.delete_body
            )
            key = None
        elif key == "X":
            self.master.view_flowdetails(self.flow)
        elif key == "z":
            if conn:
                self.flow.backup()
                e = conn.headers.get_first("content-encoding", "identity")
                if e != "identity":
                    conn.decode()
                else:
                    self.master.prompt_onekey(
                        "Select encoding: ",
                        (
                            ("gzip", "z"),
                            ("deflate", "d"),
                        ),
                        self.encode_callback,
                        conn
                    )
                self.master.refresh_flow(self.flow)
        else:
            return key

    def encode_callback(self, key, conn):
        encoding_map = {
            "z": "gzip",
            "d": "deflate",
        }
        conn.encode(encoding_map[key])
        self.master.refresh_flow(self.flow)
