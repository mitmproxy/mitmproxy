from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

from mitmproxy import controller
from mitmproxy.addons import script

import time

from test.mitmproxy import mastertest
from test.mitmproxy import tutils as ttutils


class Thing:
    def __init__(self):
        self.reply = controller.DummyReply()
        self.live = True


class TestConcurrent(mastertest.MasterTest):
    @ttutils.skip_appveyor
    def test_concurrent(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator.py"
                )
            )
            sc.start()

            f1, f2 = tflow.tflow(), tflow.tflow()
            tctx.cycle(sc, f1)
            tctx.cycle(sc, f2)
            start = time.time()
            while time.time() - start < 5:
                if f1.reply.state == f2.reply.state == "committed":
                    return
            raise ValueError("Script never acked")

    def test_concurrent_err(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/concurrent_decorator_err.py"
                )
            )
            sc.start()
            assert "decorator not supported" in tctx.master.event_log[0][1]
