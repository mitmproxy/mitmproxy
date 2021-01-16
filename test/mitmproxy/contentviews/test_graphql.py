from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy.contentviews import graphql
from . import full_eval


def test_detect_graphql():
    v = graphql.ViewGraphQL()
    assert "GraphQL" == v(b"""{"query": "query P { \\n }"}""")[0]
    assert "GraphQL" == v(b"""[{"query": "query P { \\n }"}]""")[0]
    assert "GraphQL" != v(b"""[{"xquery": "query P { \\n }"}]""")[0]


def test_format_graphql():
    assert graphql.format_graphql({ "query": "query P { \\n }" })


def test_format_query_list():
    assert graphql.format_query_list([{ "query": "query P { \\n }" }])

@given(binary())
def test_view_graphql_doesnt_crash(data):
    v = full_eval(graphql.ViewGraphQL())
    v(data)
