import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_query import query
from mitmproxy.test import tutils


def test_view_query():
    d = ""
    req = tutils.treq()
    req.query = [("foo", "bar"), ("foo", "baz")]
    out = query.prettify(d, Metadata(http_message=req))
    assert out == "foo:\n- bar\n- baz\n"

    with pytest.raises(ValueError):
        query.prettify(d, Metadata())


def test_render_priority():
    req = tutils.treq()
    req.query = [("foo", "bar"), ("foo", "baz")]
    assert query.render_priority(b"", Metadata(http_message=req))
    assert not query.render_priority(b"", Metadata())
