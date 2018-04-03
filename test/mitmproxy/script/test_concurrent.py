import pytest

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

from mitmproxy import controller
import time

from .. import tservers


class Thing:
    def __init__(self):
        self.reply = controller.DummyReply()
        self.live = True


class TestConcurrent(tservers.MasterTest):
    def test_concurrent(self):
        with taddons.context() as tctx:
            sc = tctx.script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator.py"
                )
            )
            f1, f2 = tflow.tflow(), tflow.tflow()
            tctx.cycle(sc, f1)
            tctx.cycle(sc, f2)
            start = time.time()
            while time.time() - start < 5:
                if f1.reply.state == f2.reply.state == "committed":
                    return
            raise ValueError("Script never acked")

    @pytest.mark.asyncio
    async def test_concurrent_err(self):
        with taddons.context() as tctx:
            tctx.script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator_err.py"
                )
            )
            assert await tctx.master.await_log("decorator not supported")

    def test_concurrent_class(self):
            with taddons.context() as tctx:
                sc = tctx.script(
                    tutils.test_data.path(
                        "mitmproxy/data/addonscripts/concurrent_decorator_class.py"
                    )
                )
                f1, f2 = tflow.tflow(), tflow.tflow()
                tctx.cycle(sc, f1)
                tctx.cycle(sc, f2)
                start = time.time()
                while time.time() - start < 5:
                    if f1.reply.state == f2.reply.state == "committed":
                        return
                raise ValueError("Script never acked")
