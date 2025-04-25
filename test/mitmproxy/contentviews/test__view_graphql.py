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
