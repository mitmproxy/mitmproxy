import asyncio
import os
import socket

import pytest

from mitmproxy.utils import data

pytest_plugins = ("test.full_coverage_plugin",)

skip_windows = pytest.mark.skipif(os.name == "nt", reason="Skipping due to Windows")

skip_not_windows = pytest.mark.skipif(
    os.name != "nt", reason="Skipping due to not Windows"
)

try:
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.bind(("::1", 0))
    s.close()
except OSError:
    no_ipv6 = True
else:
    no_ipv6 = False

skip_no_ipv6 = pytest.mark.skipif(no_ipv6, reason="Host has no IPv6 support")


@pytest.fixture()
def tdata():
    return data.Data(__name__)


class AsyncLogCaptureFixture:
    def __init__(self, caplog: pytest.LogCaptureFixture):
        self.caplog = caplog

    async def await_log(self, text, timeout=2):
        await asyncio.sleep(0)
        for i in range(int(timeout / 0.01)):
            if text in self.caplog.text:
                return True
            else:
                await asyncio.sleep(0.01)
        raise AssertionError(f"Did not find {text!r} in log:\n{self.caplog.text}.")


@pytest.fixture
def caplog_async(caplog):
    return AsyncLogCaptureFixture(caplog)
