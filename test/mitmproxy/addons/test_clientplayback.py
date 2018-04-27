import pytest
from unittest import mock

from mitmproxy.test import tflow
from mitmproxy import io
from mitmproxy import exceptions

from mitmproxy.addons import clientplayback
from mitmproxy.test import taddons


def tdump(path, flows):
    with open(path, "wb") as f:
        w = io.FlowWriter(f)
        for i in flows:
            w.add(i)


class MockThread():
    def is_alive(self):
        return False


class TestClientPlayback:
    # @staticmethod
    # def wait_until_not_live(flow):
    #     """
    #     Race condition: We don't want to replay the flow while it is still live.
    #     """
    #     s = time.time()
    #     while flow.live:
    #         time.sleep(0.001)
    #         if time.time() - s > 5:
    #             raise RuntimeError("Flow is live for too long.")

    # def test_replay(self):
    #     assert self.pathod("304").status_code == 304
    #     assert len(self.master.state.flows) == 1
    #     l = self.master.state.flows[-1]
    #     assert l.response.status_code == 304
    #     l.request.path = "/p/305"
    #     self.wait_until_not_live(l)
    #     rt = self.master.replay_request(l, block=True)
    #     assert l.response.status_code == 305

    #     # Disconnect error
    #     l.request.path = "/p/305:d0"
    #     rt = self.master.replay_request(l, block=True)
    #     assert rt
    #     if isinstance(self, tservers.HTTPUpstreamProxyTest):
    #         assert l.response.status_code == 502
    #     else:
    #         assert l.error

    #     # Port error
    #     l.request.port = 1
    #     # In upstream mode, we get a 502 response from the upstream proxy server.
    #     # In upstream mode with ssl, the replay will fail as we cannot establish
    #     # SSL with the upstream proxy.
    #     rt = self.master.replay_request(l, block=True)
    #     assert rt
    #     if isinstance(self, tservers.HTTPUpstreamProxyTest):
    #         assert l.response.status_code == 502
    #     else:
    #         assert l.error

    # def test_replay(self):
    #     opts = options.Options()
    #     fm = master.Master(opts)
    #     f = tflow.tflow(resp=True)
    #     f.request.content = None
    #     with pytest.raises(ReplayException, match="missing"):
    #         fm.replay_request(f)

    #     f.request = None
    #     with pytest.raises(ReplayException, match="request"):
    #         fm.replay_request(f)

    #     f.intercepted = True
    #     with pytest.raises(ReplayException, match="intercepted"):
    #         fm.replay_request(f)

    #     f.live = True
    #     with pytest.raises(ReplayException, match="live"):
    #         fm.replay_request(f)

    #     req = tutils.treq(headers=net_http.Headers(((b":authority", b"foo"), (b"header", b"qvalue"), (b"content-length", b"7"))))
    #     f = tflow.tflow(req=req)
    #     f.request.http_version = "HTTP/2.0"
    #     with mock.patch('mitmproxy.proxy.protocol.http_replay.RequestReplayThread.run'):
    #         rt = fm.replay_request(f)
    #         assert rt.f.request.http_version == "HTTP/1.1"
    #         assert ":authority" not in rt.f.request.headers

    def test_load_file(self, tmpdir):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp):
            fpath = str(tmpdir.join("flows"))
            tdump(fpath, [tflow.tflow(resp=True)])
            cp.load_file(fpath)
            assert cp.count() == 1
            with pytest.raises(exceptions.CommandError):
                cp.load_file("/nonexistent")

    def test_configure(self, tmpdir):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp) as tctx:
            path = str(tmpdir.join("flows"))
            tdump(path, [tflow.tflow()])
            assert cp.count() == 0
            tctx.configure(cp, client_replay=[path])
            assert cp.count() == 1
            tctx.configure(cp, client_replay=[])
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(cp, client_replay=["nonexistent"])

    def test_check(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp):
            f = tflow.tflow(resp=True)
            f.live = True
            assert "live flow" in cp.check(f)

            f = tflow.tflow(resp=True)
            f.intercepted = True
            assert "intercepted flow" in cp.check(f)

            f = tflow.tflow(resp=True)
            f.request = None
            assert "missing request" in cp.check(f)

            f = tflow.tflow(resp=True)
            f.request.raw_content = None
            assert "missing content" in cp.check(f)

    def test_playback(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp):
            assert cp.count() == 0
            f = tflow.tflow(resp=True)
            cp.start_replay([f])
            assert cp.count() == 1

            cp.stop_replay()
            assert cp.count() == 0