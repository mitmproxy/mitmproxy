import os
from unittest import mock

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy import io
from mitmproxy import exceptions

from mitmproxy.addons import clientplayback
from mitmproxy.test import taddons


def tdump(path, flows):
    w = io.FlowWriter(open(path, "wb"))
    for i in flows:
        w.add(i)


class MockThread():
    def is_alive(self):
        return False


class TestClientPlayback:
    def test_playback(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context():
            assert cp.count() == 0
            f = tflow.tflow(resp=True)
            cp.load([f])
            assert cp.count() == 1
            RP = "mitmproxy.proxy.protocol.http_replay.RequestReplayThread"
            with mock.patch(RP) as rp:
                assert not cp.current_thread
                cp.tick()
                assert rp.called
                assert cp.current_thread

            cp.keepserving = False
            cp.flows = None
            cp.current_thread = None
            with mock.patch("mitmproxy.master.Master.shutdown") as sd:
                cp.tick()
                assert sd.called

            cp.current_thread = MockThread()
            with mock.patch("mitmproxy.master.Master.shutdown") as sd:
                cp.tick()
                assert cp.current_thread is None

    def test_configure(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context() as tctx:
            with tutils.tmpdir() as td:
                path = os.path.join(td, "flows")
                tdump(path, [tflow.tflow()])
                tctx.configure(cp, client_replay=[path])
                tctx.configure(cp, client_replay=[])
                tctx.configure(cp)
                tutils.raises(
                    exceptions.OptionsError,
                    tctx.configure,
                    cp,
                    client_replay=["nonexistent"]
                )
