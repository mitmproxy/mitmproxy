import json
from typing import Any

from mitmproxy.contentviews import base
from mitmproxy.contentviews.json import PARSE_ERROR
from mitmproxy.contentviews.json import parse_json


def format_graphql(data):
    query = data["query"]
    header_data = data.copy()
    header_data["query"] = "..."
    return """{header}
---
{query}
""".format(header=json.dumps(header_data, indent=2), query=query)


def format_query_list(data: list[Any]):
    num_queries = len(data) - 1
    result = ""
    for i, op in enumerate(data):
        result += f"--- {i}/{num_queries}\n"
        result += format_graphql(op)
    return result


def is_graphql_query(data):
    return isinstance(data, dict) and "query" in data and "\n" in data["query"]


def is_graphql_batch_query(data):
    return (
        isinstance(data, list)
        and len(data) > 0
        and isinstance(data[0], dict)
        and "query" in data[0]
    )


class ViewGraphQL(base.View):
    name = "GraphQL"

    def __call__(self, data, **metadata):
        data = parse_json(data)
        if data is not PARSE_ERROR:
            if is_graphql_query(data):
                return "GraphQL", base.format_text(format_graphql(data))
            elif is_graphql_batch_query(data):
                return "GraphQL", base.format_text(format_query_list(data))

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        if content_type != "application/json" or not data:
            return 0

        data = parse_json(data)

        if data is not PARSE_ERROR:
            if is_graphql_query(data) or is_graphql_batch_query(data):
                return 2

        return 0
