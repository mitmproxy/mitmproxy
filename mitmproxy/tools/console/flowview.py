import sys
from functools import lru_cache

import urwid

import mitmproxy.flow
import mitmproxy.tools.console.master
import mitmproxy_rs.syntax_highlight
from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.dns import DNSMessage
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
        self.last_displayed_websocket_messages = None
        contentviews.registry.on_change.connect(self.contentview_changed)

    @property
    def view(self):
        return self.master.view

    @property
    def flow(self) -> mitmproxy.flow.Flow:
        return self.master.view.focus.flow

    def contentview_changed(self, view):
        # this is called when a contentview addon is live-reloaded.
        # we clear our cache and then rerender
        self._get_content_view.cache_clear()
        if self.master.window.current_window("flowview"):
            self.show()

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
                    (self.tab_tcp_stream, self.view_message_stream),
                    (self.tab_details, self.view_details),
                ]
            elif isinstance(f, udp.UDPFlow):
                self.tabs = [
                    (self.tab_udp_stream, self.view_message_stream),
                    (self.tab_details, self.view_details),
                ]
            elif isinstance(f, dns.DNSFlow):
                self.tabs = [
                    (self.tab_dns_request, self.view_dns_request),
                    (self.tab_dns_response, self.view_dns_response),
                    (self.tab_details, self.view_details),
                ]
            self.show()
        else:
            # Get the top window from the focus stack (the currently active view).
            # If it's NOT the "flowlist", it's safe to pop back to the previous view.
            if self.master.window.focus_stack().stack[-1] != "flowlist":
                self.master.window.pop()
            # If it is the "flowlist", we’re already at the main view with no flows to show.
            # Popping now would close the last window and prompt app exit, so we remain on the empty flow list screen instead.

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

        # there is no good way to detect what part of the flow is intercepted,
        # so we apply some heuristics to see if it's the HTTP response.
        websocket_started = flow.websocket and len(flow.websocket.messages) != 0
        response_is_intercepted = (
            self.flow.intercepted and flow.response and not websocket_started
        )
        if response_is_intercepted:
            return "Response intercepted"
        else:
            return "Response"

    def tab_dns_request(self) -> str:
        flow = self.flow
        assert isinstance(flow, dns.DNSFlow)
        if self.flow.intercepted and not flow.response:
            return "Request intercepted"
        else:
            return "Request"

    def tab_dns_response(self) -> str:
        flow = self.flow
        assert isinstance(flow, dns.DNSFlow)
        if self.flow.intercepted and flow.response:
            return "Response intercepted"
        else:
            return "Response"

    def tab_tcp_stream(self):
        return "TCP Stream"

    def tab_udp_stream(self):
        return "UDP Stream"

    def tab_websocket_messages(self):
        flow = self.flow
        assert isinstance(flow, http.HTTPFlow)
        assert flow.websocket

        if self.flow.intercepted and len(flow.websocket.messages) != 0:
            return "WebSocket Messages intercepted"
        else:
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

    def view_dns_request(self):
        flow = self.flow
        assert isinstance(flow, dns.DNSFlow)
        return self.dns_message_text("request", flow.request)

    def view_dns_response(self):
        flow = self.flow
        assert isinstance(flow, dns.DNSFlow)
        return self.dns_message_text("response", flow.response)

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
                    ("heading", "["),
                    ("heading_key", "m"),
                    ("heading", (":%s]" % viewmode)),
                ],
                align="right",
            ),
        ]
        contentview_status_bar = urwid.AttrMap(urwid.Columns(cols), "heading")
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
            pretty = contentviews.prettify_message(m, flow, viewmode)
            chunks = mitmproxy_rs.syntax_highlight.highlight(
                pretty.text,
                language=pretty.syntax_highlight,
            )
            if m.from_client:
                marker = self.FROM_CLIENT_MARKER
            else:
                marker = self.TO_CLIENT_MARKER
            widget_lines.append(urwid.Text([marker, *chunks]))

        if flow.websocket.closed_by_client is not None:
            widget_lines.append(
                urwid.Text(
                    [
                        (
                            self.FROM_CLIENT_MARKER
                            if flow.websocket.closed_by_client
                            else self.TO_CLIENT_MARKER
                        ),
                        (
                            "alert"
                            if flow.websocket.close_code in (1000, 1001, 1005)
                            else "error",
                            f"Connection closed: {flow.websocket.close_code} {flow.websocket.close_reason}",
                        ),
                    ]
                )
            )

        if flow.intercepted:
            markup = widget_lines[-1].get_text()[0]
            widget_lines[-1].set_text(("intercept", markup))

        widget_lines.insert(
            0, self._contentview_status_bar(viewmode.capitalize(), viewmode)
        )

        if (last_view := self.last_displayed_websocket_messages) is not None:
            last_view.walker[:] = widget_lines
            view = last_view
        else:
            view = searchable.Searchable(widget_lines)
            self.last_displayed_websocket_messages = view

        return view

    def view_message_stream(self) -> urwid.Widget:
        flow = self.flow
        assert isinstance(flow, (tcp.TCPFlow, udp.UDPFlow))

        if not flow.messages:
            return searchable.Searchable([urwid.Text(("highlight", "No messages."))])

        viewmode = self.master.commands.call("console.flowview.mode")

        widget_lines = []
        for m in flow.messages:
            if m.from_client:
                marker = self.FROM_CLIENT_MARKER
            else:
                marker = self.TO_CLIENT_MARKER
            pretty = contentviews.prettify_message(m, flow, viewmode)
            chunks = mitmproxy_rs.syntax_highlight.highlight(
                pretty.text,
                language=pretty.syntax_highlight,
            )

            widget_lines.append(urwid.Text([marker, *chunks]))

        if flow.intercepted:
            markup = widget_lines[-1].get_text()[0]
            widget_lines[-1].set_text(("intercept", markup))

        widget_lines.insert(
            0, self._contentview_status_bar(viewmode.capitalize(), viewmode)
        )

        return searchable.Searchable(widget_lines)

    def view_details(self):
        return flowdetailview.flowdetails(self.view, self.flow)

    def content_view(
        self, viewmode: str, message: http.Message
    ) -> tuple[str, list[urwid.Text]]:
        if message.raw_content is None:
            return "", [urwid.Text([("error", "[content missing]")])]
        elif message.raw_content == b"":
            if isinstance(message, http.Request):
                return "", [urwid.Text("No request content")]
            else:
                return "", [urwid.Text("No content")]
        else:
            full = self.master.commands.execute(
                "view.settings.getval @focus fullcontents false"
            )
            if full == "true":
                limit = sys.maxsize
            else:
                limit = ctx.options.content_view_lines_cutoff

            flow_modify_cache_invalidation = hash(
                (
                    message.raw_content,
                    message.headers.fields,
                    getattr(message, "path", None),
                )
            )
            # we need to pass the message off-band because it's not hashable
            self._get_content_view_message = message
            return self._get_content_view(
                viewmode, limit, flow_modify_cache_invalidation
            )

    @lru_cache(maxsize=200)
    def _get_content_view(
        self, viewmode: str, max_lines: int, _
    ) -> tuple[str, list[urwid.Text]]:
        message: http.Message = self._get_content_view_message
        self._get_content_view_message = None  # type: ignore[assignment]

        pretty = contentviews.prettify_message(message, self.flow, viewmode)
        cut_off = strutils.cut_after_n_lines(pretty.text, max_lines)

        chunks = mitmproxy_rs.syntax_highlight.highlight(
            cut_off,
            language=pretty.syntax_highlight,
        )

        text_objects = [urwid.Text(chunks)]
        if len(cut_off) < len(pretty.text):
            text_objects.append(
                urwid.Text(
                    [
                        (
                            "highlight",
                            "Stopped displaying data after %d lines. Press "
                            % max_lines,
                        ),
                        ("key", "f"),
                        ("highlight", " to load all data."),
                    ]
                )
            )

        return f"{pretty.view_name} {pretty.description}", text_objects

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
            txt = common.format_keyvals(hdrs, key_format="header")
            viewmode = self.master.commands.call("console.flowview.mode")
            msg, body = self.content_view(viewmode, conn)

            txt.append(self._contentview_status_bar(msg, viewmode))
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
                ),
            ]
        return searchable.Searchable(txt)

    def dns_message_text(
        self, type: str, message: DNSMessage | None
    ) -> searchable.Searchable:
        """
        Alternative:
        if not message:
            return searchable.Searchable([urwid.Text(("highlight", f"No {typ}."))])

        viewmode = self.master.commands.call("console.flowview.mode")
        pretty = contentviews.prettify_message(message, flow, viewmode)
        chunks = mitmproxy_rs.syntax_highlight.highlight(
            pretty.text,
            language=pretty.syntax_highlight,
        )

        widget_lines = [
            self._contentview_status_bar(viewmode.capitalize(), viewmode),
            urwid.Text(chunks)
        ]
        return searchable.Searchable(widget_lines)
        """
        # Keep in sync with web/src/js/components/FlowView/DnsMessages.tsx
        if message:

            def rr_text(rr: dns.ResourceRecord):
                return urwid.Text(
                    f"  {rr.name} {dns.types.to_str(rr.type)} {dns.classes.to_str(rr.class_)} {rr.ttl} {rr}"
                )

            txt = []
            txt.append(
                urwid.Text(
                    "{recursive}Question".format(
                        recursive="Recursive " if message.recursion_desired else "",
                    )
                )
            )
            txt.extend(
                urwid.Text(
                    f"  {q.name} {dns.types.to_str(q.type)} {dns.classes.to_str(q.class_)}"
                )
                for q in message.questions
            )
            txt.append(urwid.Text(""))
            txt.append(
                urwid.Text(
                    "{authoritative}{recursive}Answer".format(
                        authoritative="Authoritative "
                        if message.authoritative_answer
                        else "",
                        recursive="Recursive " if message.recursion_available else "",
                    )
                )
            )
            txt.extend(map(rr_text, message.answers))
            txt.append(urwid.Text(""))
            txt.append(urwid.Text("Authority"))
            txt.extend(map(rr_text, message.authorities))
            txt.append(urwid.Text(""))
            txt.append(urwid.Text("Addition"))
            txt.extend(map(rr_text, message.additionals))
            return searchable.Searchable(txt)
        else:
            return searchable.Searchable([urwid.Text(("highlight", f"No {type}."))])


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
