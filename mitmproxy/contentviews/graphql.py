import re
import json

import typing

from mitmproxy.contentviews import base
from mitmproxy.contentviews.json import format_json

PARSE_ERROR = object()


def parse_json(s: bytes) -> typing.Any:
    try:
        return json.loads(s.decode('utf-8'))
    except ValueError:
        return PARSE_ERROR


def format_graphql(data):
    query = data["query"]
    header_data = data.copy()
    del header_data["query"]
    return """{header}
---
{query}
""".format(header=json.dumps(header_data, indent=2), query = query)

class ViewGraphQL(base.View):
    name = "GraphQL"
    content_types = [
        "application/json",
    ]

    def __call__(self, data, **metadata):
        data = parse_json(data)
        if data is not PARSE_ERROR:
            # TODO: Batched graphql queries
            # isinstance(data, list) and "operationName" in data[0]
            if "operationName" in data:
                return "GraphQL", base.format_text(format_graphql(data))
            else:
                return "JSON", format_json(data);
