import asyncio

from mitmproxy.tools import main
from mitmproxy.test import tutils

shutdown_script = tutils.test_data.path("mitmproxy/data/addonscripts/shutdown.py")


def test_mitmweb(event_loop):
    asyncio.set_event_loop(event_loop)
    main.mitmweb([
        "--no-web-open-browser",
        "-s", shutdown_script,
        "-q", "-p", "0",
    ])


def test_mitmdump(event_loop):
    asyncio.set_event_loop(event_loop)
    main.mitmdump([
        "-s", shutdown_script,
        "-q", "-p", "0",
    ])
