from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy.contentviews import graphql
from . import full_eval


def test_detect_graphql():
    v = full_eval(json.ViewGraphQL())
    assert "GraphQL" == v("""{"query": "query P { \n }"}""")[1]
    assert "GraphQL" == v("""[{"query": "query P { \n }"}]""")[1]
    assert "GraphQL" != v("""[{"xquery": "query P { \n }"}]""")[1]


@given(binary())
def test_view_graphql_doesnt_crash(data):
    v = full_eval(json.ViewGraphQL())
    v(data)
