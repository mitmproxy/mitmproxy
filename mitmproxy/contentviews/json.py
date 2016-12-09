import json
from typing import Optional

from mitmproxy.contentviews.base import format_text, View


def pretty_json(s: bytes) -> Optional[bytes]:
    try:
        p = json.loads(s.decode('utf-8'))
    except ValueError:
        return None
    pretty = json.dumps(p, sort_keys=True, indent=4, ensure_ascii=False)
    if isinstance(pretty, str):
        # json.dumps _may_ decide to return unicode, if the JSON object is not ascii.
        # From limited testing this is always valid utf8 (otherwise json.loads will fail earlier),
        # so we can just re-encode it here.
        return pretty.encode("utf8", "strict")
    return pretty


class ViewJSON(View):
    name = "JSON"
    prompt = ("json", "s")
    content_types = [
        "application/json",
        "application/vnd.api+json"
    ]

    def __call__(self, data, **metadata):
        pj = pretty_json(data)
        if pj:
            return "JSON", format_text(pj)
