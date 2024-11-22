from __future__ import annotations

import asyncio
import os
import platform
import socket
import sys

import pytest

from mitmproxy.utils import data

skip_windows = pytest.mark.skipif(os.name == "nt", reason="Skipping due to Windows")

skip_not_windows = pytest.mark.skipif(
    os.name != "nt", reason="Skipping due to not Windows"
)

skip_not_linux = pytest.mark.skipif(
    platform.system() != "Linux", reason="Skipping due to not Linux"
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


class EagerTaskCreationEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        loop = super().new_event_loop()
        if sys.version_info >= (3, 12):
            loop.set_task_factory(asyncio.eager_task_factory)
        return loop


@pytest.fixture(scope="session")
def event_loop_policy(request):
    return EagerTaskCreationEventLoopPolicy()


@pytest.fixture()
def tdata():
    return data.Data(__name__)


class AsyncLogCaptureFixture:
    def __init__(self, caplog: pytest.LogCaptureFixture):
        self.caplog = caplog

    def set_level(self, level: int | str, logger: str | None = None) -> None:
        self.caplog.set_level(level, logger)

    async def await_log(self, text, timeout=2):
        await asyncio.sleep(0)
        for i in range(int(timeout / 0.01)):
            if text in self.caplog.text:
                return True
            else:
                await asyncio.sleep(0.01)
        raise AssertionError(f"Did not find {text!r} in log:\n{self.caplog.text}")

    def clear(self) -> None:
        self.caplog.clear()


@pytest.fixture
def caplog_async(caplog):
    return AsyncLogCaptureFixture(caplog)
