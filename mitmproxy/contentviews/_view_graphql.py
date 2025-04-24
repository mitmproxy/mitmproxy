import json
from typing import Any

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


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


class GraphQLContentview(Contentview):
    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        gql = json.loads(data)
        if is_graphql_query(gql):
            return format_graphql(gql)
        elif is_graphql_batch_query(gql):
            return format_query_list(gql)
        else:
            raise ValueError("Not a GraphQL message.")

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        if metadata.content_type != "application/json" or not data:
            return 0

        try:
            data = json.loads(data)
            if is_graphql_query(data) or is_graphql_batch_query(data):
                return 2
        except ValueError:
            pass

        return 0


graphql = GraphQLContentview()
