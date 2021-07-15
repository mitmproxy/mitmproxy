import urwid
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import base
from mitmproxy.utils import strutils


class Column(base.Column):
    def Display(self, data):
        return Display(data)

    def Edit(self, data):
        return Edit(data)

    def blank(self):
        return b""

    def keypress(self, key, editor):
        if key in ["m_select"]:
            editor.walker.start_edit()
        else:
            return key


class Display(base.Cell):
    def __init__(self, data: bytes) -> None:
        self.data = data
        escaped = strutils.bytes_to_escaped_str(data)
        w = urwid.Text(escaped, wrap="any")
        super().__init__(w)

    def get_data(self) -> bytes:
        return self.data


class Edit(base.Cell):
    def __init__(self, data: bytes) -> None:
        d = strutils.bytes_to_escaped_str(data)
        w = urwid.Edit(edit_text=d, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        super().__init__(w)

    def get_data(self) -> bytes:
        txt = self._w.get_text()[0].strip()
        try:
            return strutils.escaped_str_to_bytes(txt)
        except ValueError:
            signals.status_message.send(
                self,
                message="Invalid data.",
                expire=1000
            )
            raise
