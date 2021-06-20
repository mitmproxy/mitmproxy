import asyncio

from mitmproxy.tools import main


shutdown_script = "mitmproxy/data/addonscripts/shutdown.py"


def test_mitmweb(event_loop, tdata):
    asyncio.set_event_loop(event_loop)
    main.mitmweb([
        "--no-web-open-browser",
        "-s", tdata.path(shutdown_script),
        "-q", "-p", "0", "--web-port", "0",
    ])


def test_mitmdump(event_loop, tdata):
    asyncio.set_event_loop(event_loop)
    main.mitmdump([
        "-s", tdata.path(shutdown_script),
        "-q", "-p", "0",
    ])
