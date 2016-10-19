from test.mitmproxy import tutils, mastertest
from mitmproxy import controller
from mitmproxy.builtins import script
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import master
import time


class Thing:
    def __init__(self):
        self.reply = controller.DummyReply()
        self.live = True


class TestConcurrent(mastertest.MasterTest):
    @tutils.skip_appveyor
    def test_concurrent(self):
        m = master.Master(options.Options(), proxy.DummyServer())
        sc = script.Script(
            tutils.test_data.path(
                "data/addonscripts/concurrent_decorator.py"
            )
        )
        m.addons.add(sc)
        f1, f2 = tutils.tflow(), tutils.tflow()
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
                "data/addonscripts/concurrent_decorator_err.py"
            )
        )
        with m.handlecontext():
            sc.start()
        assert "decorator not supported" in m.event_log[0][1]
