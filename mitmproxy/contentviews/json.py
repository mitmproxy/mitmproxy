import json
from typing import Optional

from mitmproxy.contentviews import base


def pretty_json(s: bytes) -> Optional[bytes]:
    try:
        p = json.loads(s.decode('utf-8'))
    except ValueError:
        return None
    pretty = json.dumps(p, sort_keys=True, indent=4, ensure_ascii=False)
    return pretty.encode("utf8", "strict")


class ViewJSON(base.View):
    name = "JSON"
    prompt = ("json", "s")
    content_types = [
        "application/json",
        "application/vnd.api+json"
    ]

    def __call__(self, data, **metadata):
        pj = pretty_json(data)
        if pj:
            return "JSON", base.format_text(pj)
