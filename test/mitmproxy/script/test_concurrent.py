import asyncio
import os
import time

import pytest

from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestConcurrent:
    @pytest.mark.parametrize(
        "addon", ["concurrent_decorator.py", "concurrent_decorator_class.py"]
    )
    async def test_concurrent(self, addon, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path(f"mitmproxy/data/addonscripts/{addon}"))
            f1, f2 = tflow.tflow(), tflow.tflow()
            start = time.time()
            await asyncio.gather(
                tctx.cycle(sc, f1),
                tctx.cycle(sc, f2),
            )
            end = time.time()
            # This test may fail on overloaded CI systems, increase upper bound if necessary.
            if os.environ.get("CI"):
                assert 0.5 <= end - start
            else:
                assert 0.5 <= end - start < 1

    def test_concurrent_err(self, tdata, caplog):
        with taddons.context() as tctx:
            tctx.script(
                tdata.path("mitmproxy/data/addonscripts/concurrent_decorator_err.py")
            )
            assert "decorator not supported" in caplog.text
