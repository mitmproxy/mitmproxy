from mitmproxy.utils import strutils
from . import base


class ViewHex(base.View):
    name = "Hex"
    prompt = ("hex", "e")

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
