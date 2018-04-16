import pytest

from mitmproxy.tools import main
from mitmproxy import ctx


@pytest.mark.asyncio
async def test_mitmweb(event_loop):
    main.mitmweb([
        "--no-web-open-browser",
        "-q", "-p", "0",
    ])
    await ctx.master._shutdown()


@pytest.mark.asyncio
async def test_mitmdump():
    main.mitmdump(["-q", "-p", "0"])
    await ctx.master._shutdown()
