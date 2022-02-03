import asyncio
import time

import pytest

from mitmproxy import controller

from mitmproxy.test import tflow
from mitmproxy.test import taddons


class Thing:
    def __init__(self):
        self.reply = controller.DummyReply()
        self.live = True


class TestConcurrent:
    @pytest.mark.asyncio
    async def test_concurrent(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(
                tdata.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator.py"
                )
            )
            f1, f2 = tflow.tflow(), tflow.tflow()
            start = time.time()
            await asyncio.gather(
                tctx.cycle(sc, f1),
                tctx.cycle(sc, f2),
            )
            end = time.time()
            assert 0.3 < end - start < 0.7

    @pytest.mark.asyncio
    async def test_concurrent_err(self, tdata):
        with taddons.context() as tctx:
            tctx.script(
                tdata.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator_err.py"
                )
            )
            await tctx.master.await_log("decorator not supported")

    @pytest.mark.asyncio
    async def test_concurrent_class(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(
                tdata.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator_class.py"
                )
            )
            f1, f2 = tflow.tflow(), tflow.tflow()
            start = time.time()
            await asyncio.gather(
                tctx.cycle(sc, f1),
                tctx.cycle(sc, f2),
            )
            end = time.time()
            assert 0.3 < end - start < 0.7
