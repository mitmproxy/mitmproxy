from mitmproxy import contentviews
from mitmproxy.contentviews.base import format_text
from mitmproxy.test import tflow


class TContentView(contentviews.View):
    name = "Test View"

    def __call__(self, data, **metadata):
        return "TContentView", format_text("test_content")

    def render_priority(self, data, *, content_type=None, **metadata) -> float:
        return 2


async def test_contentview_flowview(console):
    assert "Flows" in console.screen_contents()
    flow = tflow.tflow()
    flow.request.headers["content-type"] = "text/html"
    await console.load_flow(flow)
    assert ">>" in console.screen_contents()
    console.type("<enter>")
    assert "Flow Details" in console.screen_contents()
    assert "XML" in console.screen_contents()

    view = TContentView()
    contentviews.add(view)
    assert "XML" not in console.screen_contents()
    assert "TContentView" in console.screen_contents()
    contentviews.remove(view)
    assert "XML" in console.screen_contents()
    assert "TContentView" not in console.screen_contents()

    console.type("q")
    assert "Flows" in console.screen_contents()
    contentviews.add(view)
    console.type("<enter>")
    assert "Flow Details" in console.screen_contents()
    assert "TContentView" in console.screen_contents()
