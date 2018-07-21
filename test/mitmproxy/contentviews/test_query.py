from mitmproxy.contentviews import query
from mitmproxy.coretypes import multidict
from . import full_eval


def test_view_query():
    d = ""
    v = full_eval(query.ViewQuery())
    f = v(d, query=multidict.MultiDictView(lambda: [("foo", "bar"), ("foo", "baz")], lambda: None))
    assert f[0] == "Query"
    assert f[1] == [[("header", "foo: "), ("text", "bar")], [("header", "foo: "), ("text", "baz")]]

    assert v(d) == ("Query", [])
