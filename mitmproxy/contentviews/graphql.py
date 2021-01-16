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


def format_query_list(data: List[Dict]):
    num_queries = len(data) - 1
    result = ""
    for i, op in enumerate(data):
        result += "--- {i}/{num_queries}\n".format(i=i, num_queries=num_queries)
        result += format_graphql(op)
    return result


class ViewGraphQL(base.View):
    name = "GraphQL"
    content_types = [
        "application/json",
    ]

    def __call__(self, data, **metadata):
        data = parse_json(data)
        if data is not PARSE_ERROR:
            if isinstance(data, list) and "query" in data[0]:
                return "GraphQL", base.format_text(format_query_list(data))
            elif "query" in data and '\n' in data["query"]:
                return "GraphQL", base.format_text(format_graphql(data))
            else:
                return "JSON", format_json(data)
