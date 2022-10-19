from mitmproxy.addons.server_side_events import ServerSideEvents
from mitmproxy.test.tflow import tflow


async def test_simple(caplog):
    s = ServerSideEvents()
    f = tflow(resp=True)
    f.response.headers["content-type"] = "text/event-stream"
    s.response(f)
    assert "mitmproxy currently does not support server side events" in caplog.text
