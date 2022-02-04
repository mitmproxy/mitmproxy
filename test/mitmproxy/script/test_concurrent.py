import asyncio
import time

import pytest

from mitmproxy.test import tflow
from mitmproxy.test import taddons


class TestConcurrent:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("addon", ["concurrent_decorator.py", "concurrent_decorator_class.py"])
    async def test_concurrent(self, addon, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(
                tdata.path(
                    f"mitmproxy/data/addonscripts/{addon}"
                )
            )
            f1, f2 = tflow.tflow(), tflow.tflow()
            start = time.time()
            await asyncio.gather(
                tctx.cycle(sc, f1),
                tctx.cycle(sc, f2),
            )
            end = time.time()
            # This test may fail on overloaded CI systems, increase upper bound if necessary.
            assert 0.3 < end - start < 1

    @pytest.mark.asyncio
    async def test_concurrent_err(self, tdata):
        with taddons.context() as tctx:
            tctx.script(
                tdata.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator_err.py"
                )
            )
            await tctx.master.await_log("decorator not supported")
