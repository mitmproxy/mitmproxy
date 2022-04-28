from mitmproxy.addons.server_side_events import ServerSideEvents
from mitmproxy.test import taddons
from mitmproxy.test.tflow import tflow


async def test_simple():
    s = ServerSideEvents()
    with taddons.context() as tctx:
        f = tflow(resp=True)
        f.response.headers["content-type"] = "text/event-stream"
        s.response(f)
        await tctx.master.await_log(
            "mitmproxy currently does not support server side events."
        )
