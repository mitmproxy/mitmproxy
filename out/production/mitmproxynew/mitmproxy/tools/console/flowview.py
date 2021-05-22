import math
import sys
from functools import lru_cache
from typing import Optional, Union  # noqa

import mitmproxy.flow
import mitmproxy.tools.console.master  # noqa
import urwid
from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy.tools.console import common
from mitmproxy.tools.console import flowdetailview
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import searchable
from mitmproxy.tools.console import tabs
from mitmproxy.utils import strutils


class SearchError(Exception):
    pass


class FlowViewHeader(urwid.WidgetWrap):

    def __init__(
        self,
        master: "mitmproxy.tools.console.master.ConsoleMaster",
    ) -> None:
        self.master = master
        self.focus_changed()

    def focus_changed(self):
        cols, _ = self.master.ui.get_cols_rows()
        if self.master.view.focus.flow:
            self._w = common.format_flow(
                self.master.view.focus.flow,
                render_mode=common.RenderMode.DETAILVIEW,
                hostheader=self.master.options.showhost,
            )
        else:
            self._w = urwid.Pile([])


class FlowDetails(tabs.Tabs):
    def __init__(self, master):
        self.master = master
        super().__init__([])
        self.show()
        self.last_displayed_body = None

    @property
    def view(self):
        return self.master.view

    @property
    def flow(self) -> mitmproxy.flow.Flow:
        return self.master.view.focus.flow

    def focus_changed(self):
        f = self.flow
        if f:
            if isinstance(f, http.HTTPFlow):
                if f.websocket:
                    self.tabs = [
                        (self.tab_http_request, self.view_request),
                        (self.tab_http_response, self.view_response),
                        (self.tab_websocket_messages, self.view_websocket_messages),
                        (self.tab_details, self.view_details),
                    ]
                else:
                    self.tabs = [
                        (self.tab_http_request, self.view_request),
                        (self.tab_http_response, self.view_response),
                        (self.tab_details, self.view_details),
                    ]
            elif isinstance(f, tcp.TCPFlow):
                self.tabs = [
                    (self.tab_tcp_stream, self.view_tcp_stream),
                    (self.tab_details, self.view_details),
                ]
            self.show()
        else:
            self.master.window.pop()

    def tab_http_request(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        if self.flow.intercepted and not flow.response:
            return "Request intercepted"
        else:
            return "Request"

    def tab_http_response(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        if self.flow.intercepted and flow.response:
            return "Response intercepted"
        else:
            return "Response"

    def tab_tcp_stream(self):
        return "TCP Stream"

    def tab_websocket_messages(self):
        return "WebSocket Messages"

    def tab_details(self):
        return "Detail"

    def view_request(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        return self.conn_text(flow.request)

    def view_response(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        return self.conn_text(flow.response)

    def _contentview_status_bar(self, description: str, viewmode: str):
        cols = [
            urwid.Text(
                [
                    ("heading", description),
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
        contentview_status_bar = urwid.AttrWrap(urwid.Columns(cols), "heading")
        return contentview_status_bar

    FROM_CLIENT_MARKER = ("from_client", f"{common.SYMBOL_FROM_CLIENT} ")
    TO_CLIENT_MARKER = ("to_client", f"{common.SYMBOL_TO_CLIENT} ")

    def view_websocket_messages(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        assert flow.websocket is not None

        if not flow.websocket.messages:
            return searchable.Searchable([urwid.Text(("highlight", "No messages."))])

        viewmode = self.master.commands.call("console.flowview.mode")

        widget_lines = []
        for m in flow.websocket.messages:
            _, lines, _ = contentviews.get_message_content_view(viewmode, m, flow)

            for line in lines:
                if m.from_client:
                    line.insert(0, self.FROM_CLIENT_MARKER)
                else:
                    line.insert(0, self.TO_CLIENT_MARKER)

                widget_lines.append(urwid.Text(line))

        if flow.websocket.closed_by_client is not None:
            widget_lines.append(urwid.Text([
                (self.FROM_CLIENT_MARKER if flow.websocket.closed_by_client else self.TO_CLIENT_MARKER),
                ("alert" if flow.websocket.close_code in (1000, 1001, 1005) else "error",
                 f"Connection closed: {flow.websocket.close_code} {flow.websocket.close_reason}")
            ]))

        if flow.intercepted:
            markup = widget_lines[-1].get_text()[0]
            widget_lines[-1].set_text(("intercept", markup))

        widget_lines.insert(0, self._contentview_status_bar(viewmode.capitalize(), viewmode))

        return searchable.Searchable(widget_lines)

    def view_tcp_stream(self) -> urwid.Widget:
        flow = self.flow
        assert isinstance(flow, tcp.TCPFlow)

        if not flow.messages:
            return searchable.Searchable([urwid.Text(("highlight", "No messages."))])

        viewmode = self.master.commands.call("console.flowview.mode")

        # Merge adjacent TCP "messages". For detailed explanation of this code block see:
        # https://github.com/mitmproxy/mitmproxy/pull/3970/files/469bd32582f764f9a29607efa4f5b04bd87961fb#r418670880
        from_client = None
        messages = []
        for message in flow.messages:
            if message.from_client is not from_client:
                messages.append(message.content)
                from_client = message.from_client
            else:
                messages[-1] += message.content

        widget_lines = []

        from_client = flow.messages[0].from_client
        for m in messages:
            _, lines, _ = contentviews.get_tcp_content_view(viewmode, m, flow)

            for line in lines:
                if from_client:
                    line.insert(0, self.FROM_CLIENT_MARKER)
                else:
                    line.insert(0, self.TO_CLIENT_MARKER)

                widget_lines.append(urwid.Text(line))

            from_client = not from_client

        if flow.intercepted:
            markup = widget_lines[-1].get_text()[0]
            widget_lines[-1].set_text(("intercept", markup))

        widget_lines.insert(0, self._contentview_status_bar(viewmode.capitalize(), viewmode))

        return searchable.Searchable(widget_lines)

    def view_details(self):
        return flowdetailview.flowdetails(self.view, self.flow)

    def content_view(self, viewmode, message):
        if message.raw_content is None:
            msg, body = "", [urwid.Text([("error", "[content missing]")])]
            return msg, body
        else:
            full = self.master.commands.execute("view.settings.getval @focus fullcontents false")
            if full == "true":
                limit = sys.maxsize
            else:
                limit = ctx.options.content_view_lines_cutoff

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
            viewmode, message, self.flow
        )
        if error:
            self.master.log.debug(error)
        # Give hint that you have to tab for the response.
        if description == "No content" and isinstance(message, http.Request):
            description = "No request content"

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

    def conn_text(self, conn):
        if conn:
            hdrs = []
            for k, v in conn.headers.fields:
                # This will always force an ascii representation of headers. For example, if the server sends a
                #
                #     X-Authors: Made with ❤ in Hamburg
                #
                # header, mitmproxy will display the following:
                #
                #     X-Authors: Made with \xe2\x9d\xa4 in Hamburg.
                #
                # The alternative would be to just use the header's UTF-8 representation and maybe
                # do `str.replace("\t", "\\t")` to exempt tabs from urwid's special characters escaping [1].
                # That would in some terminals allow rendering UTF-8 characters, but the mapping
                # wouldn't be bijective, i.e. a user couldn't distinguish "\\t" and "\t".
                # Also, from a security perspective, a mitmproxy user couldn't be fooled by homoglyphs.
                #
                # 1) https://github.com/mitmproxy/mitmproxy/issues/1833
                #    https://github.com/urwid/urwid/blob/6608ee2c9932d264abd1171468d833b7a4082e13/urwid/display_common.py#L35-L36,

                k = strutils.bytes_to_escaped_str(k) + ":"
                v = strutils.bytes_to_escaped_str(v)
                hdrs.append((k, v))
            txt = common.format_keyvals(
                hdrs,
                key_format="header"
            )
            viewmode = self.master.commands.call("console.flowview.mode")
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
        return searchable.Searchable(txt)


class FlowView(urwid.Frame, layoutwidget.LayoutWidget):
    keyctx = "flowview"
    title = "Flow Details"

    def __init__(self, master):
        super().__init__(
            FlowDetails(master),
            header=FlowViewHeader(master),
        )
        self.master = master

    def focus_changed(self, *args, **kwargs):
        self.body.focus_changed()
        self.header.focus_changed()
