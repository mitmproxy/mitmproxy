from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import InteractiveContentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._view_raw import raw
from mitmproxy_rs.contentviews import msgpack


class ExampleContentview(InteractiveContentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.decode()

    def reencode(self, prettified: str, metadata: Metadata) -> bytes:
        return prettified.encode()


class FailingContentview(Contentview):
    def prettify(self, data, metadata):
        raise ValueError("prettify error")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        raise ValueError("render_priority error")


def test_simple():
    view = ExampleContentview()
    assert view.name == "Example"
    assert view.render_priority(b"test", Metadata()) == 0
    assert view.syntax_highlight == "none"
    assert not (view < view)


def test_default_impls():
    t = ExampleContentview()
    assert t.name == "Example"
    assert t.syntax_highlight == "none"
    assert t.render_priority(b"data", Metadata()) == 0
    assert t < raw
    assert not raw < t
    assert msgpack < raw
    assert not raw < msgpack
    assert not msgpack < msgpack
