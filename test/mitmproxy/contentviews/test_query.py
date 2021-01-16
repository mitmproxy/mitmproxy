from mitmproxy.contentviews import query
from mitmproxy.test import tutils
from . import full_eval


def test_view_query():
    d = ""
    v = full_eval(query.ViewQuery())
    req = tutils.treq()
    req.query = [("foo", "bar"), ("foo", "baz")]
    f = v(d, http_message=req)
    assert f[0] == "Query"
    assert f[1] == [[("header", "foo: "), ("text", "bar")], [("header", "foo: "), ("text", "baz")]]

    assert v(d) == ("Query", [])
