from mitmproxy.utils import strutils
from . import base


class ViewHex(base.View):
    name = "Hex"

    @staticmethod
    def _format(data):
        for offset, hexa, s in strutils.hexdump(data):
            yield [
                ("offset", offset + " "),
                ("text", hexa + "   "),
                ("text", s)
            ]

    def __call__(self, data, **metadata):
        return "Hex", self._format(data)

    def render_priority(self, data: bytes, **metadata) -> float:
        return 0.2 * strutils.is_mostly_bin(data)
