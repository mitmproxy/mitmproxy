from __future__ import absolute_import, division
import os
import traceback
import sys

import math
import urwid

from netlib import odict
from netlib.http import Headers
from . import common, grideditor, signals, searchable, tabs
from . import flowdetailview
from .. import utils, controller, contentviews
from ..models import HTTPRequest, HTTPResponse, decoded
from ..exceptions import ContentViewException


class SearchError(Exception):
    pass


def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("b", "save request/response body"),
        ("D", "duplicate flow"),
        ("d", "delete flow"),
        ("E", "export"),
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
        ("P", "copy request/response (content/headers) to clipboard"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("v", "view body in external viewer"),
        ("w", "save all flows matching current limit"),
        ("W", "save this flow"),
        ("x", "delete body"),
        ("z", "encode/decode a request/response"),
        ("tab", "next tab"),
        ("h, l", "previous tab, next tab"),
        ("space", "next flow"),
        ("|", "run script on this flow"),
        ("/", "search (case sensitive)"),
        ("n", "repeat search forward"),
        ("N", "repeat search backwards"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()

footer = [
    ('heading_key', "?"), ":help ",
    ('heading_key', "q"), ":back ",
]


class FlowViewHeader(urwid.WidgetWrap):

    def __init__(self, master, f):
        self.master, self.flow = master, f
        self._w = common.format_flow(
            f,
            False,
            extended=True,
            hostheader=self.master.showhost
        )
        signals.flow_change.connect(self.sig_flow_change)

    def sig_flow_change(self, sender, flow):
        if flow == self.flow:
            self._w = common.format_flow(
                flow,
                False,
                extended=True,
                hostheader=self.master.showhost
            )


cache = utils.LRUCache(200)

TAB_REQ = 0
TAB_RESP = 1


class FlowView(tabs.Tabs):
    highlight_color = "focusfield"

    def __init__(self, master, state, flow, tab_offset):
        self.master, self.state, self.flow = master, state, flow
        tabs.Tabs.__init__(self,
                           [
                               (self.tab_request, self.view_request),
                               (self.tab_response, self.view_response),
                               (self.tab_details, self.view_details),
                           ],
                           tab_offset
                           )
        self.show()
        self.last_displayed_body = None
        signals.flow_change.connect(self.sig_flow_change)

    def tab_request(self):
        if self.flow.intercepted and not self.flow.reply.acked and not self.flow.response:
            return "Request intercepted"
        else:
            return "Request"

    def tab_response(self):
        if self.flow.intercepted and not self.flow.reply.acked and self.flow.response:
            return "Response intercepted"
        else:
            return "Response"

    def tab_details(self):
        return "Detail"

    def view_request(self):
        return self.conn_text(self.flow.request)

    def view_response(self):
        return self.conn_text(self.flow.response)

    def view_details(self):
        return flowdetailview.flowdetails(self.state, self.flow)

    def sig_flow_change(self, sender, flow):
        if flow == self.flow:
            self.show()

    def content_view(self, viewmode, message):
        if message.content is None:
            msg, body = "", [urwid.Text([("error", "[content missing]")])]
            return msg, body
        else:
            full = self.state.get_flow_setting(
                self.flow,
                (self.tab_offset, "fullcontents"),
                False
            )
            if full:
                limit = sys.maxsize
            else:
                limit = contentviews.VIEW_CUTOFF
            return cache.get(
                self._get_content_view,
                viewmode,
                message,
                limit,
                (bytes(message.headers), message.content)  # Cache invalidation
            )

    def _get_content_view(self, viewmode, message, max_lines, _):

        try:
            query = None
            if isinstance(message, HTTPRequest):
                query = message.query
            description, lines = contentviews.get_content_view(
                viewmode, message.content, headers=message.headers, query=query
            )
        except ContentViewException:
            s = "Content viewer failed: \n" + traceback.format_exc()
            signals.add_event(s, "error")
            description, lines = contentviews.get_content_view(
                contentviews.get("Raw"), message.content, headers=message.headers
            )
            description = description.replace("Raw", "Couldn't parse: falling back to Raw")

        # Give hint that you have to tab for the response.
        if description == "No content" and isinstance(message, HTTPRequest):
            description = "No request content (press tab to view response)"

        # If the users has a wide terminal, he gets fewer lines; this should not be an issue.
        chars_per_line = 80
        max_chars = max_lines * chars_per_line
        total_chars = 0
        text_objects = []
        for line in lines:
            txt = []
            for (style, text) in line:
                if total_chars + len(text) > max_chars:
                    text = text[:max_chars - total_chars]
                txt.append((style, text))
                total_chars += len(text)
                if total_chars == max_chars:
                    break

            # round up to the next line.
            total_chars = int(math.ceil(total_chars / chars_per_line) * chars_per_line)

            text_objects.append(urwid.Text(txt))
            if total_chars == max_chars:
                text_objects.append(urwid.Text([
                    ("highlight", "Stopped displaying data after %d lines. Press " % max_lines),
                    ("key", "f"),
                    ("highlight", " to load all data.")
                ]))
                break

        return description, text_objects

    def viewmode_get(self):
        override = self.state.get_flow_setting(
            self.flow,
            (self.tab_offset, "prettyview")
        )
        return self.state.default_body_view if override is None else override

    def conn_text(self, conn):
        if conn:
            txt = common.format_keyvals(
                [(h + ":", v) for (h, v) in conn.headers.fields],
                key = "header",
                val = "text"
            )
            viewmode = self.viewmode_get()
            msg, body = self.content_view(viewmode, conn)

            cols = [
                urwid.Text(
                    [
                        ("heading", msg),
                    ]
                ),
                urwid.Text(
                    [
                        " ",
                        ('heading', "["),
                        ('heading_key', "m"),
                        ('heading', (":%s]" % viewmode.name)),
                    ],
                    align="right"
                )
            ]
            title = urwid.AttrWrap(urwid.Columns(cols), "heading")

            txt.append(title)
            txt.extend(body)
        else:
            txt = [
                urwid.Text(""),
                urwid.Text(
                    [
                        ("highlight", "No response. Press "),
                        ("key", "e"),
                        ("highlight", " and edit any aspect to add one."),
                    ]
                )
            ]
        return searchable.Searchable(self.state, txt)

    def set_method_raw(self, m):
        if m:
            self.flow.request.method = m
            signals.flow_change.send(self, flow = self.flow)

    def edit_method(self, m):
        if m == "e":
            signals.status_prompt.send(
                prompt = "Method",
                text = self.flow.request.method,
                callback = self.set_method_raw
            )
        else:
            for i in common.METHOD_OPTIONS:
                if i[1] == m:
                    self.flow.request.method = i[0].upper()
            signals.flow_change.send(self, flow = self.flow)

    def set_url(self, url):
        request = self.flow.request
        try:
            request.url = str(url)
        except ValueError:
            return "Invalid URL."
        signals.flow_change.send(self, flow = self.flow)

    def set_resp_code(self, code):
        response = self.flow.response
        try:
            response.status_code = int(code)
        except ValueError:
            return None
        import BaseHTTPServer
        if int(code) in BaseHTTPServer.BaseHTTPRequestHandler.responses:
            response.msg = BaseHTTPServer.BaseHTTPRequestHandler.responses[
                int(code)][0]
        signals.flow_change.send(self, flow = self.flow)

    def set_resp_msg(self, msg):
        response = self.flow.response
        response.msg = msg
        signals.flow_change.send(self, flow = self.flow)

    def set_headers(self, fields, conn):
        conn.headers = Headers(fields)
        signals.flow_change.send(self, flow = self.flow)

    def set_query(self, lst, conn):
        conn.set_query(odict.ODict(lst))
        signals.flow_change.send(self, flow = self.flow)

    def set_path_components(self, lst, conn):
        conn.set_path_components(lst)
        signals.flow_change.send(self, flow = self.flow)

    def set_form(self, lst, conn):
        conn.set_form_urlencoded(odict.ODict(lst))
        signals.flow_change.send(self, flow = self.flow)

    def edit_form(self, conn):
        self.master.view_grideditor(
            grideditor.URLEncodedFormEditor(
                self.master,
                conn.get_form_urlencoded().lst,
                self.set_form,
                conn
            )
        )

    def edit_form_confirm(self, key, conn):
        if key == "y":
            self.edit_form(conn)

    def set_cookies(self, lst, conn):
        od = odict.ODict(lst)
        conn.set_cookies(od)
        signals.flow_change.send(self, flow = self.flow)

    def set_setcookies(self, data, conn):
        conn.set_cookies(data)
        signals.flow_change.send(self, flow = self.flow)

    def edit(self, part):
        if self.tab_offset == TAB_REQ:
            message = self.flow.request
        else:
            if not self.flow.response:
                self.flow.response = HTTPResponse(
                    self.flow.request.http_version,
                    200, "OK", Headers(), ""
                )
                self.flow.response.reply = controller.DummyReply()
            message = self.flow.response

        self.flow.backup()
        if message == self.flow.request and part == "c":
            self.master.view_grideditor(
                grideditor.CookieEditor(
                    self.master,
                    message.get_cookies().lst,
                    self.set_cookies,
                    message
                )
            )
        if message == self.flow.response and part == "c":
            self.master.view_grideditor(
                grideditor.SetCookieEditor(
                    self.master,
                    message.get_cookies(),
                    self.set_setcookies,
                    message
                )
            )
        if part == "r":
            with decoded(message):
                # Fix an issue caused by some editors when editing a
                # request/response body. Many editors make it hard to save a
                # file without a terminating newline on the last line. When
                # editing message bodies, this can cause problems. For now, I
                # just strip the newlines off the end of the body when we return
                # from an editor.
                c = self.master.spawn_editor(message.content or "")
                message.content = c.rstrip("\n")
        elif part == "f":
            if not message.get_form_urlencoded() and message.content:
                signals.status_prompt_onekey.send(
                    prompt = "Existing body is not a URL-encoded form. Clear and edit?",
                    keys = [
                        ("yes", "y"),
                        ("no", "n"),
                    ],
                    callback = self.edit_form_confirm,
                    args = (message,)
                )
            else:
                self.edit_form(message)
        elif part == "h":
            self.master.view_grideditor(
                grideditor.HeaderEditor(
                    self.master,
                    message.headers.fields,
                    self.set_headers,
                    message
                )
            )
        elif part == "p":
            p = message.get_path_components()
            self.master.view_grideditor(
                grideditor.PathEditor(
                    self.master,
                    p,
                    self.set_path_components,
                    message
                )
            )
        elif part == "q":
            self.master.view_grideditor(
                grideditor.QueryEditor(
                    self.master,
                    message.get_query().lst,
                    self.set_query, message
                )
            )
        elif part == "u":
            signals.status_prompt.send(
                prompt = "URL",
                text = message.url,
                callback = self.set_url
            )
        elif part == "m":
            signals.status_prompt_onekey.send(
                prompt = "Method",
                keys = common.METHOD_OPTIONS,
                callback = self.edit_method
            )
        elif part == "o":
            signals.status_prompt.send(
                prompt = "Code",
                text = str(message.status_code),
                callback = self.set_resp_code
            )
        elif part == "m":
            signals.status_prompt.send(
                prompt = "Message",
                text = message.msg,
                callback = self.set_resp_msg
            )
        signals.flow_change.send(self, flow = self.flow)

    def _view_nextprev_flow(self, np, flow):
        try:
            idx = self.state.view.index(flow)
        except IndexError:
            return
        if np == "next":
            new_flow, new_idx = self.state.get_next(idx)
        else:
            new_flow, new_idx = self.state.get_prev(idx)
        if new_flow is None:
            signals.status_message.send(message="No more flows!")
        else:
            signals.pop_view_state.send(self)
            self.master.view_flow(new_flow, self.tab_offset)

    def view_next_flow(self, flow):
        return self._view_nextprev_flow("next", flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow("prev", flow)

    def change_this_display_mode(self, t):
        self.state.add_flow_setting(
            self.flow,
            (self.tab_offset, "prettyview"),
            contentviews.get_by_shortcut(t)
        )
        signals.flow_change.send(self, flow = self.flow)

    def delete_body(self, t):
        if t == "m":
            val = None
        else:
            val = None
        if self.tab_offset == TAB_REQ:
            self.flow.request.content = val
        else:
            self.flow.response.content = val
        signals.flow_change.send(self, flow = self.flow)

    def keypress(self, size, key):
        key = super(self.__class__, self).keypress(size, key)

        if key == " ":
            self.view_next_flow(self.flow)
            return

        key = common.shortcuts(key)
        if self.tab_offset == TAB_REQ:
            conn = self.flow.request
        elif self.tab_offset == TAB_RESP:
            conn = self.flow.response
        else:
            conn = None

        if key in ("up", "down", "page up", "page down"):
            # Why doesn't this just work??
            self._w.keypress(size, key)
        elif key == "a":
            self.flow.accept_intercept(self.master)
            signals.flow_change.send(self, flow = self.flow)
        elif key == "A":
            self.master.accept_all()
            signals.flow_change.send(self, flow = self.flow)
        elif key == "d":
            if self.state.flow_count() == 1:
                self.master.view_flowlist()
            elif self.state.view.index(self.flow) == len(self.state.view) - 1:
                self.view_prev_flow(self.flow)
            else:
                self.view_next_flow(self.flow)
            f = self.flow
            f.kill(self.master)
            self.state.delete_flow(f)
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.view_flow(f)
            signals.status_message.send(message="Duplicated.")
        elif key == "p":
            self.view_prev_flow(self.flow)
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                signals.status_message.send(message=r)
            signals.flow_change.send(self, flow = self.flow)
        elif key == "V":
            if not self.flow.modified():
                signals.status_message.send(message="Flow not modified.")
                return
            self.state.revert(self.flow)
            signals.flow_change.send(self, flow = self.flow)
            signals.status_message.send(message="Reverted.")
        elif key == "W":
            signals.status_prompt_path.send(
                prompt = "Save this flow",
                callback = self.master.save_one_flow,
                args = (self.flow,)
            )
        elif key == "E":
            signals.status_prompt_onekey.send(
                self,
                prompt = "Export",
                keys = (
                    ("as curl command", "c"),
                    ("as python code", "p"),
                    ("as raw request", "r"),
                    ("as locust code", "l"),
                    ("as locust task", "t"),
                ),
                callback = common.export_prompt,
                args = (self.flow,)
            )
        elif key == "|":
            signals.status_prompt_path.send(
                prompt = "Send flow to script",
                callback = self.master.run_script_once,
                args = (self.flow,)
            )

        if not conn and key in set(list("befgmxvz")):
            signals.status_message.send(
                message = "Tab to the request or response",
                expire = 1
            )
        elif conn:
            if key == "b":
                if self.tab_offset == TAB_REQ:
                    common.ask_save_body(
                        "q", self.master, self.state, self.flow
                    )
                else:
                    common.ask_save_body(
                        "s", self.master, self.state, self.flow
                    )
            elif key == "e":
                if self.tab_offset == TAB_REQ:
                    signals.status_prompt_onekey.send(
                        prompt = "Edit request",
                        keys = (
                            ("cookies", "c"),
                            ("query", "q"),
                            ("path", "p"),
                            ("url", "u"),
                            ("header", "h"),
                            ("form", "f"),
                            ("raw body", "r"),
                            ("method", "m"),
                        ),
                        callback = self.edit
                    )
                else:
                    signals.status_prompt_onekey.send(
                        prompt = "Edit response",
                        keys = (
                            ("cookies", "c"),
                            ("code", "o"),
                            ("message", "m"),
                            ("header", "h"),
                            ("raw body", "r"),
                        ),
                        callback = self.edit
                    )
                key = None
            elif key == "f":
                signals.status_message.send(message="Loading all body data...")
                self.state.add_flow_setting(
                    self.flow,
                    (self.tab_offset, "fullcontents"),
                    True
                )
                signals.flow_change.send(self, flow = self.flow)
                signals.status_message.send(message="")
            elif key == "P":
                if self.tab_offset == TAB_REQ:
                    scope = "q"
                else:
                    scope = "s"
                common.ask_copy_part(scope, self.flow, self.master, self.state)
            elif key == "m":
                p = list(contentviews.view_prompts)
                p.insert(0, ("Clear", "C"))
                signals.status_prompt_onekey.send(
                    self,
                    prompt = "Display mode",
                    keys = p,
                    callback = self.change_this_display_mode
                )
                key = None
            elif key == "x":
                signals.status_prompt_onekey.send(
                    prompt = "Delete body",
                    keys = (
                        ("completely", "c"),
                        ("mark as missing", "m"),
                    ),
                    callback = self.delete_body
                )
                key = None
            elif key == "v":
                if conn.content:
                    t = conn.headers.get("content-type")
                    if "EDITOR" in os.environ or "PAGER" in os.environ:
                        self.master.spawn_external_viewer(conn.content, t)
                    else:
                        signals.status_message.send(
                            message = "Error! Set $EDITOR or $PAGER."
                        )
            elif key == "z":
                self.flow.backup()
                e = conn.headers.get("content-encoding", "identity")
                if e != "identity":
                    if not conn.decode():
                        signals.status_message.send(
                            message = "Could not decode - invalid data?"
                        )
                else:
                    signals.status_prompt_onekey.send(
                        prompt = "Select encoding: ",
                        keys = (
                            ("gzip", "z"),
                            ("deflate", "d"),
                        ),
                        callback = self.encode_callback,
                        args = (conn,)
                    )
                signals.flow_change.send(self, flow = self.flow)
        return key

    def encode_callback(self, key, conn):
        encoding_map = {
            "z": "gzip",
            "d": "deflate",
        }
        conn.encode(encoding_map[key])
        signals.flow_change.send(self, flow = self.flow)
