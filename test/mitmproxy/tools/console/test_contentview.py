from mitmproxy import contentviews
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews import raw
from mitmproxy.test import tflow


class ConsoleTestContentView(contentviews.Contentview):
    def __init__(self, content: str):
        self.content = content

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return self.content

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return 2


async def test_contentview_flowview(console, monkeypatch):
    monkeypatch.setattr(contentviews.registry, "_by_name", {"raw": raw})
    assert "Flows" in console.screen_contents()
    await console.load_flow(tflow.tflow())
    assert ">>" in console.screen_contents()
    console.type("<enter>")
    assert "Raw" in console.screen_contents()

    view = ConsoleTestContentView("test1")
    contentviews.add(view)
    assert "test1" in console.screen_contents()

    console.type("q")
    assert "Flows" in console.screen_contents()

    contentviews.add(ConsoleTestContentView("test2"))
    console.type("<enter>")
    assert "test2" in console.screen_contents()
