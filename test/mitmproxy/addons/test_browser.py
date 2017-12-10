from unittest import mock

from mitmproxy.addons import browser
from mitmproxy.test import taddons


def test_browser():
    with mock.patch("subprocess.Popen") as po:
        b = browser.Browser()
        with taddons.context() as tctx:
            b.start()
            assert po.called
            b.start()

            assert not tctx.master.has_log("already running")
            b.browser.poll = lambda: None
            b.start()
            assert tctx.master.has_log("already running")
            b.done()
            assert not b.browser
