import re
import json
from typing import Optional

from mitmproxy.contentviews import base


def pretty_json(s: bytes) -> Optional[bytes]:
    try:
        p = json.loads(s.decode('utf-8'))
    except ValueError:
        return None
    return p


class ViewJSON(base.View):
    name = "JSON"
    content_types = [
        "application/json",
        "application/json-rpc",
        "application/vnd.api+json"
    ]

    @staticmethod
    def _format(pj):
        li = []
        for chunk in json.JSONEncoder(indent=4, sort_keys=True, ensure_ascii=False).iterencode(pj):
            k = re.split("\\n", chunk)
            if(len(k) > 1):
                if(len(k[0]) > 0):
                    li.append(('text', k[0]))
                yield li
                li = []
                chunk = k[1]
            else:
                chunk = k[0]
            if(re.match('^\s*\".*\"$', chunk)):
                li.append(('json_string', chunk))
            elif(re.match('\s*[0-9]+[.]{0,1}[0-9]*', chunk)):
                li.append(('json_number', chunk))
            elif(re.match('\s*true|null|false', chunk)):
                li.append(('json_boolean', chunk))
            else:
                li.append(('text', chunk))
        yield li

    def __call__(self, data, **metadata):
        pj = pretty_json(data)
        if pj is not None:
            return "JSON", self._format(pj)
