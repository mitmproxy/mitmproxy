import pytest

from mitmproxy.test import tutils
from mitmproxy.tools import main

shutdown_script = tutils.test_data.path("mitmproxy/data/addonscripts/shutdown.py")


@pytest.mark.asyncio
async def test_mitmweb():
    main.mitmweb([
        "--no-web-open-browser",
        "-q",
        "-p", "0",
        "-s", shutdown_script
    ])


@pytest.mark.asyncio
async def test_mitmdump():
    main.mitmdump([
        "-q",
        "-p", "0",
        "-s", shutdown_script
    ])
