from mitmproxy.contentviews import query
from mitmproxy.coretypes import multidict
from . import full_eval


def test_view_query():
    d = ""
    v = full_eval(query.ViewQuery())
    f = v(d, query=multidict.MultiDict([("foo", "bar")]))
    assert f[0] == "Query"
    assert f[1] == [[("header", "foo: "), ("text", "bar")]]

    assert v(d) == ("Query", [])
