import pytest

from mitmproxy import proxy
from mitmproxy.addons import termstatus
from mitmproxy.test import taddons


@pytest.mark.asyncio
async def test_configure():
    ts = termstatus.TermStatus()
    with taddons.context() as ctx:
        ctx.master.server = proxy.DummyServer()
        ctx.configure(ts, server=False)
        ts.running()
        ctx.configure(ts, server=True)
        ts.running()
        await ctx.master.await_log("server listening")
