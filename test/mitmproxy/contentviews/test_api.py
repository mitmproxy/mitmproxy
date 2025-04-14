from mitmproxy.contentviews import raw
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy_rs.contentviews import msgpack


class TestContentview(Contentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return "test"


def test_default_impls():
    t = TestContentview()
    assert t.name == "Test"
    assert t.syntax_highlight == "none"
    assert t.render_priority(b"data", Metadata()) == 0
    assert raw < t
    assert not t < raw
    assert msgpack < raw
    assert not raw < msgpack
    assert not msgpack < msgpack
