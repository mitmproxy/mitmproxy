from . import base
from mitmproxy.utils import strutils


class ViewHexDump(base.View):
    name = "Hex Dump"

    @staticmethod
    def _format(data):
        for offset, hexa, s in strutils.hexdump(data):
            yield [("offset", offset + " "), ("text", hexa + "   "), ("text", s)]

    def __call__(self, data, **metadata):
        return "Hexdump", self._format(data)

    def render_priority(self, data: bytes, **metadata) -> float:
        return 0.2 * strutils.is_mostly_bin(data)


class ViewHexStream(base.View):
    name = "Raw Hex Stream"

    def __call__(self, data, **metadata):
        return "Raw Hex Stream", base.format_text(data.hex())

    def render_priority(self, data: bytes, **metadata) -> float:
        return 0.15 * strutils.is_mostly_bin(data)
