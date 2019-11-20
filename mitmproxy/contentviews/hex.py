from mitmproxy.utils import strutils
from . import base


class ViewHex(base.View):
    name = "Hex"

    @staticmethod
    def _format(data, from_client=None, offset=0):
        for offset, hexa, s in strutils.hexdump(data, byte_offset=offset):
            if from_client is None:
                yield [
                    ("offset", offset + " "),
                    ("text", hexa + "   "),
                    ("text", s)
                ]
            elif from_client:
                yield [
                    ("offset", offset + " "),
                    ("from_client", hexa + "   "),
                    ("from_client", s)
                ]
            else:
                yield [
                    ("offset", "    " + offset + " "),
                    ("from_server", hexa + "   "),
                    ("from_server", s)
                ]


    def __call__(self, data, **metadata):
        from_client = None
        offset = 0

        if "from_client" in metadata:
            from_client = metadata['from_client']
            offset = metadata['offset']

        return "Hex", self._format(data, from_client, offset)

