
from mitmproxy.contentviews import graphql


def test_render_priority():
    v = graphql.ViewGraphQL()
    assert 2 == v.render_priority(
        b"""{"query": "query P { \\n }"}""", content_type="application/json"
    )
    assert 2 == v.render_priority(
        b"""[{"query": "query P { \\n }"}]""", content_type="application/json"
    )
    assert 0 == v.render_priority(
        b"""[{"query": "query P { \\n }"}]""", content_type="text/html"
    )
    assert 0 == v.render_priority(
        b"""[{"xquery": "query P { \\n }"}]""", content_type="application/json"
    )
    assert 0 == v.render_priority(b"""[]""", content_type="application/json")
    assert 0 == v.render_priority(b"}", content_type="application/json")


def test_format_graphql():
    assert graphql.format_graphql({"query": "query P { \\n }"})


def test_format_query_list():
    assert graphql.format_query_list([{"query": "query P { \\n }"}])


def test_view_graphql():
    v = graphql.ViewGraphQL()
    assert v(b"""{"query": "query P { \\n }"}""", content_type="application/json")
    assert v(b"""[{"query": "query P { \\n }"}]""", content_type="application/json")
