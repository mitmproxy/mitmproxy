import math
import os
import sys
from functools import lru_cache
from typing import Optional, Union  # noqa

import urwid

from mitmproxy import contentviews
from mitmproxy import exceptions
from mitmproxy import export
from mitmproxy import http
from mitmproxy.net.http import Headers
from mitmproxy.net.http import status_codes
from mitmproxy.tools.console import common
from mitmproxy.tools.console import flowdetailview
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import searchable
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import tabs


class SearchError(Exception):
    pass


def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("b", "save request/response body"),
        ("C", "export flow to clipboard"),
        ("D", "duplicate flow"),
        ("d", "delete flow"),
        ("e", "edit request/response"),
        ("f", "load full body data"),
        ("m", "change body display mode for this entity\n(default mode can be changed in the options)"),
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
        ("E", "export flow to file"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("v", "view body in external viewer"),
        ("w", "save all flows matching current view filter"),
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

    def __init__(self, master: "mitmproxy.console.master.ConsoleMaster", f: http.HTTPFlow):
        self.master = master
        self.flow = f
        self._w = common.format_flow(
            f,
            False,
            extended=True,
            hostheader=self.master.options.showhost
        )
        signals.flow_change.connect(self.sig_flow_change)

    def sig_flow_change(self, sender, flow):
        if flow == self.flow:
            self._w = common.format_flow(
                flow,
                False,
                extended=True,
                hostheader=self.master.options.showhost
            )


TAB_REQ = 0
TAB_RESP = 1


class FlowView(tabs.Tabs):
    highlight_color = "focusfield"

    def __init__(self, master, view, flow, tab_offset):
        self.master, self.view, self.flow = master, view, flow
        super().__init__(
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
        if self.flow.intercepted and not self.flow.response:
            return "Request intercepted"
        else:
            return "Request"

    def tab_response(self):
        if self.flow.intercepted and self.flow.response:
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
        return flowdetailview.flowdetails(self.view, self.flow)

    def sig_flow_change(self, sender, flow):
        if flow == self.flow:
            self.show()

    def content_view(self, viewmode, message):
        if message.raw_content is None:
            msg, body = "", [urwid.Text([("error", "[content missing]")])]
            return msg, body
        else:
            s = self.view.settings[self.flow]
            full = s.get((self.tab_offset, "fullcontents"), False)
            if full:
                limit = sys.maxsize
            else:
                limit = contentviews.VIEW_CUTOFF

            flow_modify_cache_invalidation = hash((
                message.raw_content,
                message.headers.fields,
                getattr(message, "path", None),
            ))
            # we need to pass the message off-band because it's not hashable
            self._get_content_view_message = message
            return self._get_content_view(viewmode, limit, flow_modify_cache_invalidation)

    @lru_cache(maxsize=200)
    def _get_content_view(self, viewmode, max_lines, _):
        message = self._get_content_view_message
        self._get_content_view_message = None
        description, lines, error = contentviews.get_message_content_view(
            viewmode, message
        )
        if error:
            signals.add_log(error, "error")
        # Give hint that you have to tab for the response.
        if description == "No content" and isinstance(message, http.HTTPRequest):
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
        override = self.view.settings[self.flow].get(
            (self.tab_offset, "prettyview"),
            None
        )
        return self.master.options.default_contentview if override is None else override

    def conn_text(self, conn):
        if conn:
            txt = common.format_keyvals(
                [(h + ":", v) for (h, v) in conn.headers.items(multi=True)],
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
                        ('heading', (":%s]" % viewmode)),
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
        return searchable.Searchable(self.view, txt)

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

    def set_resp_status_code(self, status_code):
        try:
            status_code = int(status_code)
        except ValueError:
            return None
        self.flow.response.status_code = status_code
        if status_code in status_codes.RESPONSES:
            self.flow.response.reason = status_codes.RESPONSES[status_code]
        signals.flow_change.send(self, flow = self.flow)

    def set_resp_reason(self, reason):
        self.flow.response.reason = reason
        signals.flow_change.send(self, flow = self.flow)

    def set_headers(self, fields, conn):
        conn.headers = Headers(fields)
        signals.flow_change.send(self, flow = self.flow)

    def set_query(self, lst, conn):
        conn.query = lst
        signals.flow_change.send(self, flow = self.flow)

    def set_path_components(self, lst, conn):
        conn.path_components = lst
        signals.flow_change.send(self, flow = self.flow)

    def set_form(self, lst, conn):
        conn.urlencoded_form = lst
        signals.flow_change.send(self, flow = self.flow)

    def edit_form(self, conn):
        self.master.view_grideditor(
            grideditor.URLEncodedFormEditor(
                self.master,
                conn.urlencoded_form.items(multi=True),
                self.set_form,
                conn
            )
        )

    def edit_form_confirm(self, key, conn):
        if key == "y":
            self.edit_form(conn)

    def set_cookies(self, lst, conn):
        conn.cookies = lst
        signals.flow_change.send(self, flow = self.flow)

    def set_setcookies(self, data, conn):
        conn.cookies = data
        signals.flow_change.send(self, flow = self.flow)

    def edit(self, part):
        if self.tab_offset == TAB_REQ:
            message = self.flow.request
        else:
            if not self.flow.response:
                self.flow.response = http.HTTPResponse.make(200, b"")
            message = self.flow.response

        self.flow.backup()
        if message == self.flow.request and part == "c":
            self.master.view_grideditor(
                grideditor.CookieEditor(
                    self.master,
                    message.cookies.items(multi=True),
                    self.set_cookies,
                    message
                )
            )
        if message == self.flow.response and part == "c":
            self.master.view_grideditor(
                grideditor.SetCookieEditor(
                    self.master,
                    message.cookies.items(multi=True),
                    self.set_setcookies,
                    message
                )
            )
        if part == "r":
            # Fix an issue caused by some editors when editing a
            # request/response body. Many editors make it hard to save a
            # file without a terminating newline on the last line. When
            # editing message bodies, this can cause problems. For now, I
            # just strip the newlines off the end of the body when we return
            # from an editor.
            c = self.master.spawn_editor(message.get_content(strict=False) or b"")
            message.content = c.rstrip(b"\n")
        elif part == "f":
            if not message.urlencoded_form and message.raw_content:
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
            p = message.path_components
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
                    message.query.items(multi=True),
                    self.set_query, message
                )
            )
        elif part == "u":
            signals.status_prompt.send(
                prompt = "URL",
                text = message.url,
                callback = self.set_url
            )
        elif part == "m" and message == self.flow.request:
            signals.status_prompt_onekey.send(
                prompt = "Method",
                keys = common.METHOD_OPTIONS,
                callback = self.edit_method
            )
        elif part == "o":
            signals.status_prompt.send(
                prompt = "Code",
                text = str(message.status_code),
                callback = self.set_resp_status_code
            )
        elif part == "m" and message == self.flow.response:
            signals.status_prompt.send(
                prompt = "Message",
                text = message.reason,
                callback = self.set_resp_reason
            )
        signals.flow_change.send(self, flow = self.flow)

    def view_flow(self, flow):
        signals.pop_view_state.send(self)
        self.master.view_flow(flow, self.tab_offset)

    def _view_nextprev_flow(self, idx, flow):
        if not self.view.inbounds(idx):
            signals.status_message.send(message="No more flows")
            return
        self.view_flow(self.view[idx])

    def view_next_flow(self, flow):
        return self._view_nextprev_flow(self.view.index(flow) + 1, flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow(self.view.index(flow) - 1, flow)

    def change_this_display_mode(self, t):
        view = contentviews.get_by_shortcut(t)
        if view:
            self.view.settings[self.flow][(self.tab_offset, "prettyview")] = view.name
        else:
            self.view.settings[self.flow][(self.tab_offset, "prettyview")] = None
        signals.flow_change.send(self, flow=self.flow)

    def keypress(self, size, key):
        conn = None  # type: Optional[Union[http.HTTPRequest, http.HTTPResponse]]
        if self.tab_offset == TAB_REQ:
            conn = self.flow.request
        elif self.tab_offset == TAB_RESP:
            conn = self.flow.response

        key = super().keypress(size, key)

        # Special case: Space moves over to the next flow.
        # We need to catch that before applying common.shortcuts()
        if key == " ":
            self.view_next_flow(self.flow)
            return

        key = common.shortcuts(key)
        if key in ("up", "down", "page up", "page down"):
            # Pass scroll events to the wrapped widget
            self._w.keypress(size, key)
        elif key == "a":
            self.flow.resume()
            self.master.view.update(self.flow)
        elif key == "A":
            for f in self.view:
                if f.intercepted:
                    f.resume()
                    self.master.view.update(self.flow)
        elif key == "d":
            if self.flow.killable:
                self.flow.kill()
            self.view.remove(self.flow)
            if not self.view.focus.flow:
                self.master.view_flowlist()
            else:
                self.view_flow(self.view.focus.flow)
        elif key == "D":
            cp = self.flow.copy()
            self.master.view.add(cp)
            self.master.view.focus.flow = cp
            self.view_flow(cp)
            signals.status_message.send(message="Duplicated.")
        elif key == "p":
            self.view_prev_flow(self.flow)
        elif key == "r":
            try:
                self.master.replay_request(self.flow)
            except exceptions.ReplayException as e:
                signals.add_log("Replay error: %s" % e, "warn")
            signals.flow_change.send(self, flow = self.flow)
        elif key == "V":
            if self.flow.modified():
                self.flow.revert()
                signals.flow_change.send(self, flow = self.flow)
                signals.status_message.send(message="Reverted.")
            else:
                signals.status_message.send(message="Flow not modified.")
        elif key == "W":
            signals.status_prompt_path.send(
                prompt = "Save this flow",
                callback = self.master.save_one_flow,
                args = (self.flow,)
            )
        elif key == "|":
            signals.status_prompt_path.send(
                prompt = "Send flow to script",
                callback = self.master.run_script_once,
                args = (self.flow,)
            )
        elif key == "e":
            if self.tab_offset == TAB_REQ:
                signals.status_prompt_onekey.send(
                    prompt="Edit request",
                    keys=(
                        ("cookies", "c"),
                        ("query", "q"),
                        ("path", "p"),
                        ("url", "u"),
                        ("header", "h"),
                        ("form", "f"),
                        ("raw body", "r"),
                        ("method", "m"),
                    ),
                    callback=self.edit
                )
            elif self.tab_offset == TAB_RESP:
                signals.status_prompt_onekey.send(
                    prompt="Edit response",
                    keys=(
                        ("cookies", "c"),
                        ("code", "o"),
                        ("message", "m"),
                        ("header", "h"),
                        ("raw body", "r"),
                    ),
                    callback=self.edit
                )
            else:
                signals.status_message.send(
                    message="Tab to the request or response",
                    expire=1
                )
        elif key in set("bfgmxvzEC") and not conn:
            signals.status_message.send(
                message = "Tab to the request or response",
                expire = 1
            )
            return
        elif key == "b":
            if self.tab_offset == TAB_REQ:
                common.ask_save_body("q", self.flow)
            else:
                common.ask_save_body("s", self.flow)
        elif key == "f":
            self.view.settings[self.flow][(self.tab_offset, "fullcontents")] = True
            signals.flow_change.send(self, flow = self.flow)
            signals.status_message.send(message="Loading all body data...")
        elif key == "m":
            p = list(contentviews.view_prompts)
            p.insert(0, ("Clear", "C"))
            signals.status_prompt_onekey.send(
                self,
                prompt = "Display mode",
                keys = p,
                callback = self.change_this_display_mode
            )
        elif key == "E":
            if self.tab_offset == TAB_REQ:
                scope = "q"
            else:
                scope = "s"
            signals.status_prompt_onekey.send(
                self,
                prompt = "Export to file",
                keys = [(e[0], e[1]) for e in export.EXPORTERS],
                callback = common.export_to_clip_or_file,
                args = (scope, self.flow, common.ask_save_path)
            )
        elif key == "C":
            if self.tab_offset == TAB_REQ:
                scope = "q"
            else:
                scope = "s"
            signals.status_prompt_onekey.send(
                self,
                prompt = "Export to clipboard",
                keys = [(e[0], e[1]) for e in export.EXPORTERS],
                callback = common.export_to_clip_or_file,
                args = (scope, self.flow, common.copy_to_clipboard_or_prompt)
            )
        elif key == "x":
            conn.content = None
            signals.flow_change.send(self, flow=self.flow)
        elif key == "v":
            if conn.raw_content:
                t = conn.headers.get("content-type")
                if "EDITOR" in os.environ or "PAGER" in os.environ:
                    self.master.spawn_external_viewer(conn.get_content(strict=False), t)
                else:
                    signals.status_message.send(
                        message = "Error! Set $EDITOR or $PAGER."
                    )
        elif key == "z":
            self.flow.backup()
            e = conn.headers.get("content-encoding", "identity")
            if e != "identity":
                try:
                    conn.decode()
                except ValueError:
                    signals.status_message.send(
                        message = "Could not decode - invalid data?"
                    )
            else:
                signals.status_prompt_onekey.send(
                    prompt = "Select encoding: ",
                    keys = (
                        ("gzip", "z"),
                        ("deflate", "d"),
                        ("brotli", "b"),
                    ),
                    callback = self.encode_callback,
                    args = (conn,)
                )
            signals.flow_change.send(self, flow = self.flow)
        else:
            # Key is not handled here.
            return key

    def encode_callback(self, key, conn):
        encoding_map = {
            "z": "gzip",
            "d": "deflate",
            "b": "brotli",
        }
        conn.encode(encoding_map[key])
        signals.flow_change.send(self, flow = self.flow)
