import typing

import urwid

from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import base
from mitmproxy.utils import strutils

strbytes = typing.Union[str, bytes]


class Column(base.Column):
    def Display(self, data):
        return Display(data)

    def Edit(self, data):
        return Edit(data)

    def blank(self):
        return ""

    def keypress(self, key, editor):
        if key in ["m_select"]:
            editor.walker.start_edit()
        else:
            return key


class Display(base.Cell):
    def __init__(self, data: strbytes) -> None:
        self.data = data
        if isinstance(data, bytes):
            escaped = strutils.bytes_to_escaped_str(data)
        else:
            escaped = data.encode()
        w = urwid.Text(escaped, wrap="any")
        super().__init__(w)

    def get_data(self) -> strbytes:
        return self.data


class Edit(base.Cell):
    def __init__(self, data: strbytes) -> None:
        if isinstance(data, bytes):
            escaped = strutils.bytes_to_escaped_str(data)
        else:
            escaped = data.encode()
        self.type = type(data)  # type: typing.Type
        w = urwid.Edit(edit_text=escaped, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        super().__init__(w)

    def get_data(self) -> strbytes:
        txt = self._w.get_text()[0].strip()
        try:
            if self.type == bytes:
                return strutils.escaped_str_to_bytes(txt)
            else:
                return txt.decode()
        except ValueError:
            signals.status_message.send(
                self,
                message="Invalid Python-style string encoding.",
                expire=1000
            )
            raise
