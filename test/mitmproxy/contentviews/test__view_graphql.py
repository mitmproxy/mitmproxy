import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_graphql import format_graphql
from mitmproxy.contentviews._view_graphql import format_query_list
from mitmproxy.contentviews._view_graphql import graphql


def test_render_priority():
    assert 2 == graphql.render_priority(
        b"""{"query": "query P { \\n }"}""", Metadata(content_type="application/json")
    )
    assert 2 == graphql.render_priority(
        b"""[{"query": "query P { \\n }"}]""", Metadata(content_type="application/json")
    )
    assert 0 == graphql.render_priority(
        b"""[{"query": "query P { \\n }"}]""", Metadata(content_type="text/html")
    )
    assert 0 == graphql.render_priority(
        b"""[{"xquery": "query P { \\n }"}]""",
        Metadata(content_type="application/json"),
    )
    assert 0 == graphql.render_priority(
        b"""[]""", Metadata(content_type="application/json")
    )
    assert 0 == graphql.render_priority(b"}", Metadata(content_type="application/json"))


@pytest.mark.parametrize(
    "data",
    [
        # "query" is not a GraphQL document
        b'{"query": null}',
        b'{"query": 42}',
        b'{"query": {"match": "a\\nb"}}',
        b'[{"query": null}]',
        # not all list items are GraphQL operations
        b'[{"query": "query P { \\n }"}, {"id": 1}]',
        b'[{"query": "query P { \\n }"}, 42]',
    ],
)
def test_not_graphql(data):
    metadata = Metadata(content_type="application/json")
    assert 0 == graphql.render_priority(data, metadata)
    with pytest.raises(ValueError, match="Not a GraphQL message"):
        graphql.prettify(data, metadata)


def test_format_graphql():
    assert format_graphql({"query": "query P { \\n }"})


def test_format_query_list():
    assert format_query_list([{"query": "query P { \\n }"}])


def test_view_graphql():
    assert graphql.prettify(
        b"""{"query": "query P { \\n }"}""", Metadata(content_type="application/json")
    )
    assert graphql.prettify(
        b"""[{"query": "query P { \\n }"}]""", Metadata(content_type="application/json")
    )
    with pytest.raises(ValueError):
        assert graphql.prettify(b'"valid json"', Metadata())
