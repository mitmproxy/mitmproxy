import asyncio

import pytest

from mitmproxy.options import Options
from mitmproxy.tools.web.master import WebMaster


async def test_reuse():
    async def handler(r, w):
        pass

    server = await asyncio.start_server(
        handler, host="127.0.0.1", port=0, reuse_address=False
    )
    port = server.sockets[0].getsockname()[1]
    master = WebMaster(Options(), with_termlog=False)
    master.options.web_host = "127.0.0.1"
    master.options.web_port = port
    with pytest.raises(OSError, match=f"--set web_port={port + 2}"):
        await master.running()
    server.close()
    # tornado registers some callbacks,
    # we want to run them to avoid fatal warnings.
    await asyncio.sleep(0)
