import asyncio
from unittest.mock import MagicMock

import pytest
from mitmproxy.options import Options
from mitmproxy.tools.web.master import WebMaster


async def test_reuse():
    server = await asyncio.start_server(MagicMock(), "127.0.0.1", 0)
    options = Options()
    options.add_option("web_port", int, server.sockets[0].getsockname()[1], "")
    options.add_option("web_host", str, "127.0.0.1", "")
    master = WebMaster(options)
    with pytest.raises(OSError, match=f"--set web_port={options.web_port + 1}"):
        await master.running()
    server.close()
