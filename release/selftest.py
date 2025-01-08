"""
This addons is used for binaries to perform a minimal selftest. Use like so:

  mitmdump -s selftest.py -p 0
"""

import asyncio
import logging
import ssl
import sys
from pathlib import Path

from mitmproxy import ctx
from mitmproxy.utils import asyncio_utils


def load(_):
    # force a random port
    ctx.options.listen_port = 0
    try:
        ctx.options.web_open_browser = False
    except KeyError:
        pass


def running():
    asyncio_utils.create_task(
        make_request(),
        name="selftest",
        keep_ref=True,
    )


async def make_request():
    try:
        cafile = Path(ctx.options.confdir).expanduser() / "mitmproxy-ca.pem"
        while not cafile.exists():
            await asyncio.sleep(0.01)
        ssl_ctx = ssl.create_default_context(cafile=cafile)
        port = ctx.master.addons.get("proxyserver").listen_addrs()[0][1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port, ssl=ssl_ctx)
        writer.write(b"GET / HTTP/1.1\r\nHost: mitm.it\r\nConnection: close\r\n\r\n")
        await writer.drain()
        resp = await reader.read()
        if b"This page is served by your local mitmproxy instance" not in resp:
            raise RuntimeError(resp)
        logging.info("Self-test successful.")
        ctx.master.shutdown()
    except Exception as e:
        print(f"{e!r}")
        sys.exit(1)
