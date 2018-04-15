import pytest

from mitmproxy.tools import main


@pytest.mark.asyncio
async def test_mitmweb(event_loop):
    m = main.mitmweb([
        "--no-web-open-browser",
        "-q", "-p", "0",
    ])
    await m._shutdown()


@pytest.mark.asyncio
async def test_mitmdump():
    m = main.mitmdump(["-q", "-p", "0"])
    await m._shutdown()
