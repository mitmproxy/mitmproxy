import zlib
import json
from typing import Optional

from mitmproxy.contentviews import base


"""
A custom Content Viewer for decompress some json which compress by zlib and content-type is application/octet-stream.
"""


def decompress_octet_stream_json(s: bytes) -> Optional[bytes]:
    try:
        # Check Compression Method and flag. https://tools.ietf.org/html/rfc1950
        if hex(s[0]) == '0x78' and hex(s[1]) in ['0x01', '0x5e', '0x9c', '0xda']:
            p = json.loads(zlib.decompress(s).decode('utf-8'))
        else:
            return None
    except ValueError:
        return None
    pretty = json.dumps(p, sort_keys=True, indent=4, ensure_ascii=False)
    return pretty.encode("utf8", "strict")


class ViewOctetStreamJSON(base.View):
    name = "Octet-Stream-JSON"
    prompt = ("octet_stream_json", "n")
    content_types = [
        "application/octet-stream"
    ]

    def __call__(self, data, **metadata):
        pj = decompress_octet_stream_json(data)
        if pj:
            return "Octet-Stream JSON", base.format_text(pj)
