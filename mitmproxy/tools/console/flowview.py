import math
import sys
from functools import lru_cache
from typing import Optional, Union  # noqa
from mitmproxy import exceptions
from h2.settings import _setting_code_from_int

import urwid

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import http
from mitmproxy import http2
from mitmproxy import flowfilter
from mitmproxy.tools.console import common
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import flowdetailview
from mitmproxy.tools.console import searchable
from mitmproxy.tools.console import tabs
import mitmproxy.tools.console.master  # noqa
from mitmproxy.utils import strutils


class SearchError(Exception):
    pass


class FlowViewHeader(urwid.WidgetWrap):

    def __init__(
        self,
        master: "mitmproxy.tools.console.master.ConsoleMaster",
        view
    ) -> None:
        self.master, self.view = master, view
        self.focus_changed()

    def focus_changed(self):
        cols, _ = self.master.ui.get_cols_rows()
        if self.view.focus.flow:
            if self.view.flow_type == "http1":
                self._w = common.format_flow(
                    self.view.focus.flow,
                    False,
                    extended=True,
                    hostheader=self.master.options.showhost,
                    max_url_len=cols,
                )
            elif self.view.flow_type == "http2":
                self._w = common.format_http2_item(
                    self.view.focus.flow,
                    False,
                )
            else:
                raise NotImplementedError()
        else:
            self._w = urwid.Pile([])


class FlowDetails(tabs.Tabs):
    def __init__(self, master):
        self.master = master
        super().__init__([])
        self.show()
        self.last_displayed_body = None

    @property
    def flow(self):
        return self.view.focus.flow


class FlowDetailsHttp1(FlowDetails):
    def focus_changed(self):
        if self.view.focus.flow:
            self.tabs = [
                (self.tab_request, self.view_request),
                (self.tab_response, self.view_response),
                (self.tab_details, self.view_details),
                (self.tab_http2, self.view_http2)
            ]
            self.show()
        else:
            self.master.window.pop()

    @property
    def view(self):
        return self.master.views['http1']

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

    def tab_http2(self):
        return "HTTP/2"

    def view_request(self):
        return self.conn_text(self.flow.request)

    def view_response(self):
        return self.conn_text(self.flow.response)

    def view_details(self):
        return flowdetailview.flowdetails(self.view, self.flow)

    def view_http2(self):
        if (self.flow.client_stream_id and self.flow.server_stream_id and
            self.flow.server_conn and self.flow.server_conn.address and
            self.flow.client_conn and self.flow.client_conn.address):
            dst_addr = "{}:{}".format(self.flow.server_conn.address[0], self.flow.server_conn.address[1])
            src_addr = "{}:{}".format(self.flow.client_conn.address[0], self.flow.client_conn.address[1])
            self.master.commands.execute("view.http2.filter.set '( ( (~sid %s | ~f.pushed_stream_id %s) & ~fc ) | ( (~sid %s | ~f.pushed_stream_id %s) & ! ~fc ) ) & ~src %s & ~dst %s'" %
                (self.flow.client_stream_id, self.flow.client_stream_id,
                self.flow.server_stream_id, self.flow.server_stream_id,
                src_addr, dst_addr))
            #flt = flowfilter.parse(
                #"( ( (~sid %s | ~f.pushed_stream_id %s) & ~fc ) | ( (~sid %s | ~f.pushed_stream_id %s) & ! ~fc ) ) & ~src %s & ~dst %s" %
                #(self.flow.client_stream_id, self.flow.client_stream_id,
                #self.flow.server_stream_id, self.flow.server_stream_id,
                #src_addr, dst_addr))
            return flowlist.FlowListBox(self.master, self.master.views['http2'])
        else:
            txt = [
                urwid.Text(""),
                urwid.Text(
                    [
                        ("highlight", "No HTTP/2 Exchange"),
                    ]
                )
            ]
            return searchable.Searchable(txt)

    def content_view(self, viewmode, message):
        if message.raw_content is None:
            msg, body = "", [urwid.Text([("error", "[content missing]")])]
            return msg, body
        else:
            full = self.master.commands.execute("view.http1.settings.getval @focus fullcontents false")
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
            viewmode, message
        )
        if error:
            self.master.log.debug(error)
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


class FlowDetailsHttp2(FlowDetails):
    def focus_changed(self):
        if self.view.focus.flow:
            self.tabs = [
                (self.tab_frame, self.view_frame),
                (self.tab_details, self.view_details),
            ]
            self.show()
        else:
            self.master.window.pop()

    @property
    def view(self):
        return self.master.views['http2']

    def tab_frame(self):
        return "Frame"

    def tab_details(self):
        return "Detail"

    def view_frame(self):
        return self.conn_text(self.flow)

    def view_details(self):
        return flowdetailview.flowdetails(self.view, self.flow)

    def _frame_base(self, frame):
        base_frame_info = [
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
            ]
        return common.format_keyvals(base_frame_info, indent=4)

    def _format_headers(self, frame):
        static_field = []
        dynamic_field = []
        header_index = 0
        headers = list(frame.headers)
        for hpack_h in frame.hpack_info['static']:
            for h in headers:
                if h[0] == hpack_h[0] and h[1] == hpack_h[1]:
                    static_field.append((str(header_index), h[0], h[1]))
                    headers.remove(h)
            header_index += 1

        for hpack_h in frame.hpack_info['dynamic']:
            hpack_h_val = hpack_h[1] if not isinstance(hpack_h[1], memoryview) else hpack_h[1].tobytes()
            for h in headers:
                if h[0] == hpack_h[0] and h[1] == hpack_h_val:
                    dynamic_field.append((str(header_index), h[0], h[1]))
                    headers.remove(h)
                header_index += 1
        for h in headers:
            dynamic_field.append(("", h[0], h[1]))

        txt = [urwid.Text([("head", "Static Header fields")])]
        txt.extend(common.format_keyvals(static_field))
        txt.append(urwid.Text([("head", "Dynamic Header fields")]))
        txt.extend(common.format_keyvals(dynamic_field))
        return txt

    def _frame_header(self, frame):
        txt = common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("End stream", str(frame.end_stream))
            ], indent=4)
        if frame.priority:
            txt.append(urwid.Text([("head", "Priority informations")]))
            txt.extend(common.format_keyvals([
                    ("Weight", str(frame.priority['weight'])),
                    ("Depends on", str(frame.priority['depends_on'])),
                    ("Exclusive", str(frame.priority['exclusive']))
                ], indent=4))

        txt.extend(self._format_headers(frame))
        return txt

    def _frame_push(self, frame):
        txt = common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Pushed stream-ID", str(frame.pushed_stream_id))
            ], indent=4)

        txt.extend(self._format_headers(frame))
        return txt

    def _frame_data(self, frame):
        base_frame_info = [
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Flow controlled length", str(frame.length)),
                ("End stream", str(frame.end_stream))
            ]
        txt = common.format_keyvals(base_frame_info, indent=4)
        txt.append(urwid.Text([("head", "Data")]))
        data = ""
        return_nb = 0
        space_nb  = 0
        for b in frame.data.hex():
            data += b
            if space_nb == 3:
                data += " "
                if return_nb == 7:
                    data += "\n"
                return_nb = (return_nb + 1) % 8
            space_nb = (space_nb + 1) % 4
        txt.append(urwid.Text([("text", data)]))
        return txt

    def _frame_windows_update(self, frame):
        return common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Delta", str(frame.delta)),
            ], indent=4)

    def _frame_settings(self, frame):
        txt = common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Ack", str(frame.ack))
            ], indent=4)
        txt.append(urwid.Text([("head", "Settings")]))
        settings = []
        for key, val in frame.settings.items():
            key_name = str(_setting_code_from_int(key)).split('.')[1]
            settings.append((key_name, str(val['new_value'])))
        txt.extend(common.format_keyvals(settings, indent=4))
        return txt

    def _frame_ping(self, frame):
        base_frame_info = [
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Ack", str(frame.ack)),
            ]
        txt = common.format_keyvals(base_frame_info, indent=4)
        txt.append(urwid.Text([("head", "Ping data")]))
        data = ""
        return_nb = 0
        space_nb  = 0
        for b in frame.data.hex():
            data += b
            if space_nb == 3:
                data += " "
                if return_nb == 7:
                    data += "\n"
                return_nb = (return_nb + 1) % 8
            space_nb = (space_nb + 1) % 4
        txt.append(urwid.Text([("text", data)]))
        return txt

    def _frame_priority_update(self, frame):
        return common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Weight", str(frame.priority['weight'])),
                ("Depends on", str(frame.priority['depends_on'])),
                ("Exclusive", str(frame.priority['exclusive']))
            ], indent=4)

    def _frame_reset_stream(self, frame):
        return common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Error code", str(frame.error_code)),
                ("Remote reset", str(frame.remote_reset)),
            ], indent=4)

    def _frame_goaway(self, frame):
        return common.format_keyvals([
                ("Type", frame.frame_type),
                ("Stream-ID", str(frame.stream_id)),
                ("Last stream-ID", str(frame.last_stream_id)),
                ("Error code", str(frame.error_code)),
                ("Additional data", str(frame.additional_data)),
            ], indent=4)

    def conn_text(self, frame):
        if isinstance(frame, http2.Http2Header):
            txt = self._frame_header(frame)
        elif isinstance(frame, http2.Http2Push):
            txt = self._frame_push(frame)
        elif isinstance(frame, http2.Http2Data):
            txt = self._frame_data(frame)
        elif isinstance(frame, http2.Http2WindowsUpdate):
            txt = self._frame_windows_update(frame)
        elif isinstance(frame, http2.Http2Settings):
            txt = self._frame_settings(frame)
        elif isinstance(frame, http2.Http2Ping):
            txt = self._frame_ping(frame)
        elif isinstance(frame, http2.Http2PriorityUpdate):
            txt = self._frame_priority_update(frame)
        elif isinstance(frame, http2.Http2RstStream):
            txt = self._frame_reset_stream(frame)
        elif isinstance(frame, http2.Http2Goaway):
            txt = self._frame_goaway(frame)
        elif isinstance(frame, http2.HTTP2Frame):
            txt = self._frame_base(frame)
        else:
            raise exceptions.TypeError("Unknown frame type: %s" % frame)
 
        return searchable.Searchable(txt)


class FlowView(urwid.Frame, layoutwidget.LayoutWidget):
    def __init__(self, master, view):
        if view.flow_type == "http1":
            super().__init__(
                FlowDetailsHttp1(master),
                header = FlowViewHeader(master, view),
            )
        if view.flow_type == "http2":
            super().__init__(
                FlowDetailsHttp2(master),
                header = FlowViewHeader(master, view),
            )
        self.master, self.view = master, view
        self.title = "Flow Details %s" % self.view.flow_type
        self.keyctx = "flowview_%s" % self.view.flow_type

    def focus_changed(self, *args, **kwargs):
        self.body.focus_changed()
        self.header.focus_changed()
