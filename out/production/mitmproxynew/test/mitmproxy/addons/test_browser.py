from unittest import mock
import pytest

from mitmproxy.addons import browser
from mitmproxy.test import taddons


@pytest.mark.asyncio
async def test_browser():
    with mock.patch("subprocess.Popen") as po, mock.patch("shutil.which") as which:
        which.return_value = "chrome"
        b = browser.Browser()
        with taddons.context() as tctx:
            b.start()
            assert po.called

            b.start()
            await tctx.master.await_log("Starting additional browser")
            assert len(b.browser) == 2
            b.done()
            assert not b.browser


@pytest.mark.asyncio
async def test_no_browser():
    with mock.patch("shutil.which") as which:
        which.return_value = False

        b = browser.Browser()
        with taddons.context() as tctx:
            b.start()
            await tctx.master.await_log("platform is not supported")
