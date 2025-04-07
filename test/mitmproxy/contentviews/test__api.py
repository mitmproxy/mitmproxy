from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import InteractiveContentview
from mitmproxy.contentviews._api import Metadata


class ExampleContentview(InteractiveContentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.decode()

    def reencode(self, prettified: str, metadata: Metadata) -> bytes:
        return prettified.encode()


class FailingContentview(Contentview):
    def prettify(self, data, metadata):
        raise ValueError("Test error")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        return 1


def test_simple():
    view = ExampleContentview()
    assert view.name == "Example"
    assert view.render_priority(b"test", Metadata()) == 0
    assert view.syntax_highlight == "none"
    assert not (view < view)
