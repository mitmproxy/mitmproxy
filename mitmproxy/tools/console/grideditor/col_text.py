"""
Welcome to the encoding dance!

In a nutshell, text columns are actually a proxy class for byte columns,
which just encode/decodes contents.
"""

from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import col_bytes


class Column(col_bytes.Column):
    def __init__(self, heading, encoding="utf8", errors="surrogateescape"):
        super().__init__(heading)
        self.encoding_args = encoding, errors

    def Display(self, data):
        return TDisplay(data, self.encoding_args)

    def Edit(self, data):
        return TEdit(data, self.encoding_args)

    def blank(self):
        return u""


# This is the same for both edit and display.
class EncodingMixin:
    def __init__(self, data: str, encoding_args) -> "TDisplay":
        self.encoding_args = encoding_args
        data = data.encode(*self.encoding_args)
        super().__init__(data)

    def get_data(self) -> str:
        data = super().get_data()
        try:
            return data.decode(*self.encoding_args)
        except ValueError:
            signals.status_message.send(
                self,
                message="Invalid encoding.",
                expire=1000
            )
            raise


# urwid forces a different name for a subclass.
class TDisplay(EncodingMixin, col_bytes.Display):
    pass


class TEdit(EncodingMixin, col_bytes.Edit):
    pass
