import zlib
import json
from typing import Optional

from mitmproxy.contentviews import base


def decompress_stream_json(s: bytes) -> Optional[bytes]:
    try:
        if s[0] == 120:
            p = json.loads(zlib.decompress(s).decode('utf-8'))
        else:
            return None
    except ValueError:
        return None
    pretty = json.dumps(p, sort_keys=True, indent=4, ensure_ascii=False)
    return pretty.encode("utf8", "strict")


class ViewStreamJSON(base.View):
    name = "Stream_JSON"
    prompt = ("stream_json", "n")
    content_types = [
        "application/octet-stream"
    ]

    def __call__(self, data, **metadata):
        pj = decompress_stream_json(data)
        if pj:
            return "JSON", base.format_text(pj)
