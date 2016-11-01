from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy import controller
from mitmproxy.addons import script
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import master

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
        m = master.Master(options.Options(), proxy.DummyServer())
        sc = script.Script(
            tutils.test_data.path(
                "mitmproxy/data/addonscripts/concurrent_decorator.py"
            )
        )
        m.addons.add(sc)
        f1, f2 = tflow.tflow(), tflow.tflow()
        m.request(f1)
        m.request(f2)
        start = time.time()
        while time.time() - start < 5:
            if f1.reply.state == f2.reply.state == "committed":
                return
        raise ValueError("Script never acked")

    def test_concurrent_err(self):
        m = mastertest.RecordingMaster(options.Options(), proxy.DummyServer())
        sc = script.Script(
            tutils.test_data.path(
                "mitmproxy/data/addonscripts/concurrent_decorator_err.py"
            )
        )
        with m.handlecontext():
            sc.start()
        assert "decorator not supported" in m.event_log[0][1]
