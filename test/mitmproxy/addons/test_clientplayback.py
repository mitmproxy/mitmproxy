import pytest
from unittest import mock

from mitmproxy.test import tflow
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
        with taddons.context() as tctx:
            assert cp.count() == 0
            f = tflow.tflow(resp=True)
            cp.start_replay([f])
            assert cp.count() == 1
            RP = "mitmproxy.proxy.protocol.http_replay.RequestReplayThread"
            with mock.patch(RP) as rp:
                assert not cp.current_thread
                cp.tick()
                assert rp.called
                assert cp.current_thread

            cp.flows = None
            cp.current_thread = None
            cp.tick()
            assert tctx.master.has_event("processing_complete")

            cp.current_thread = MockThread()
            cp.tick()
            assert cp.current_thread is None

            cp.start_replay([f])
            cp.stop_replay()
            assert not cp.flows

    def test_configure(self, tmpdir):
        cp = clientplayback.ClientPlayback()
        with taddons.context() as tctx:
            path = str(tmpdir.join("flows"))
            tdump(path, [tflow.tflow()])
            tctx.configure(cp, client_replay=[path])
            cp.configured = False
            tctx.configure(cp, client_replay=[])
            cp.configured = False
            tctx.configure(cp)
            cp.configured = False
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(cp, client_replay=["nonexistent"])
