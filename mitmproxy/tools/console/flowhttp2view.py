from mitmproxy import exceptions
from mitmproxy import http2
from mitmproxy.tools.console import common
from mitmproxy.tools.console import searchable

from h2.errors import ErrorCodes
from h2.settings import SettingCodes
import urwid


class Http2DetailColumns(urwid.Columns):

    def _set_focus_position(self, position):
        super()._set_focus_position(0)

    focus_position = property(urwid.Columns._get_focus_position, _set_focus_position, doc="""
        index of child widget in focus. Raises :exc:`IndexError` if read when
        Columns is empty, or when set to an invalid index.
        """)

    def update_view(self, focus):
        if focus.flow:
            self.contents[1] = conn_text(focus.flow), self.contents[1][1]
        else:
            self.contents[1] = searchable.Searchable([urwid.Text(""),urwid.Text([("highlight", "No informations")])]), self.contents[1][1]


def _frame_base(frame):
    base_frame_info = [
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
        ]
    return common.format_keyvals(base_frame_info, indent=4)


def _format_headers(frame):
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


def _frame_header(frame):
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

    txt.extend(_format_headers(frame))
    return txt


def _frame_push(frame):
    txt = common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Pushed stream-ID", str(frame.pushed_stream_id))
        ], indent=4)

    txt.extend(_format_headers(frame))
    return txt


def _frame_data(frame):
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
    space_nb = 0
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


def _frame_windows_update(frame):
    return common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Delta", str(frame.delta)),
        ], indent=4)


def _frame_settings(frame):
    txt = common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Ack", str(frame.ack))
        ], indent=4)
    txt.append(urwid.Text([("head", "Settings")]))
    settings = []
    for key, val in frame.settings.items():
        key_name = str(SettingCodes(key)).split('.')[1]
        settings.append((key_name, str(val['new_value'])))
    txt.extend(common.format_keyvals(settings, indent=4))
    return txt


def _frame_ping(frame):
    base_frame_info = [
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Ack", str(frame.ack)),
        ]
    txt = common.format_keyvals(base_frame_info, indent=4)
    txt.append(urwid.Text([("head", "Ping data")]))
    data = ""
    return_nb = 0
    space_nb = 0
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


def _frame_priority_update(frame):
    return common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Weight", str(frame.priority['weight'])),
            ("Depends on", str(frame.priority['depends_on'])),
            ("Exclusive", str(frame.priority['exclusive']))
        ], indent=4)


def _frame_reset_stream(frame):
    return common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Error code", str(ErrorCodes(frame.error_code)).split('.')[1]),
            ("Remote reset", str(frame.remote_reset)),
        ], indent=4)


def _frame_goaway(frame):
    return common.format_keyvals([
            ("Type", frame.frame_type),
            ("Stream-ID", str(frame.stream_id)),
            ("Last stream-ID", str(frame.last_stream_id)),
            ("Error code", str(ErrorCodes(frame.error_code)).split('.')[1]),
            ("Additional data", str(frame.additional_data)),
        ], indent=4)


def conn_text(frame):
    if isinstance(frame, http2.Http2Header):
        txt = _frame_header(frame)
    elif isinstance(frame, http2.Http2Push):
        txt = _frame_push(frame)
    elif isinstance(frame, http2.Http2Data):
        txt = _frame_data(frame)
    elif isinstance(frame, http2.Http2WindowsUpdate):
        txt = _frame_windows_update(frame)
    elif isinstance(frame, http2.Http2Settings):
        txt = _frame_settings(frame)
    elif isinstance(frame, http2.Http2Ping):
        txt = _frame_ping(frame)
    elif isinstance(frame, http2.Http2PriorityUpdate):
        txt = _frame_priority_update(frame)
    elif isinstance(frame, http2.Http2RstStream):
        txt = _frame_reset_stream(frame)
    elif isinstance(frame, http2.Http2Goaway):
        txt = _frame_goaway(frame)
    elif isinstance(frame, http2.HTTP2Frame):
        txt = _frame_base(frame)
    else:
        raise exceptions.TypeError("Unknown frame type: %s" % frame)

    return searchable.Searchable(txt)
