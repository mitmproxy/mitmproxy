from mitmproxy.test import tflow
import mock

from mitmproxy.addons import clientplayback
from mitmproxy import options

from .. import mastertest


class TestClientPlayback:
    def test_playback(self):
        cp = clientplayback.ClientPlayback()
        cp.configure(options.Options(), [])
        assert cp.count() == 0
        f = tflow.tflow(resp=True)
        cp.load([f])
        assert cp.count() == 1
        RP = "mitmproxy.proxy.protocol.http_replay.RequestReplayThread"
        with mock.patch(RP) as rp:
            assert not cp.current
            with mastertest.mockctx():
                cp.tick()
            rp.assert_called()
            assert cp.current

        cp.keepserving = False
        cp.flows = None
        cp.current = None
        with mock.patch("mitmproxy.master.Master.shutdown") as sd:
            with mastertest.mockctx():
                cp.tick()
            sd.assert_called()

    def test_configure(self):
        cp = clientplayback.ClientPlayback()
        cp.configure(
            options.Options(), []
        )
