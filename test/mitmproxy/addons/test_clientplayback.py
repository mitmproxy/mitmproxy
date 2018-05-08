import time
import pytest

from mitmproxy.test import tflow, tutils
from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy.net import http as net_http

from mitmproxy.addons import clientplayback
from mitmproxy.test import taddons

from .. import tservers


def tdump(path, flows):
    with open(path, "wb") as f:
        w = io.FlowWriter(f)
        for i in flows:
            w.add(i)


class MockThread():
    def is_alive(self):
        return False


class TBase(tservers.HTTPProxyTest):
    @staticmethod
    def wait_response(flow):
        """
        Race condition: We don't want to replay the flow while it is still live.
        """
        s = time.time()
        while True:
            if flow.response or flow.error:
                flow.server_conn.close()
                break
            time.sleep(0.001)
            if time.time() - s > 5:
                raise RuntimeError("Flow is live for too long.")

    @staticmethod
    def reset(f):
        f.live = False
        f.repsonse = False
        f.error = False

    def addons(self):
        return [clientplayback.ClientPlayback()]

    def test_replay(self):
        cr = self.master.addons.get("clientplayback")

        assert self.pathod("304").status_code == 304
        assert len(self.master.state.flows) == 1
        l = self.master.state.flows[-1]
        assert l.response.status_code == 304
        l.request.path = "/p/305"
        l.response = None
        cr.start_replay([l])
        self.wait_response(l)
        assert l.response.status_code == 305

        # Disconnect error
        cr.stop_replay()
        self.reset(l)
        l.request.path = "/p/305:d0"
        cr.start_replay([l])
        self.wait_response(l)
        if isinstance(self, tservers.HTTPUpstreamProxyTest):
            assert l.response.status_code == 502
        else:
            assert l.error

        # # Port error
        cr.stop_replay()
        self.reset(l)
        l.request.port = 1
        # In upstream mode, we get a 502 response from the upstream proxy server.
        # In upstream mode with ssl, the replay will fail as we cannot establish
        # SSL with the upstream proxy.
        cr.start_replay([l])
        self.wait_response(l)
        if isinstance(self, tservers.HTTPUpstreamProxyTest):
            assert l.response.status_code == 502
        else:
            assert l.error


class TestHTTPProxy(TBase, tservers.HTTPProxyTest):
    pass


class TestHTTPSProxy(TBase, tservers.HTTPProxyTest):
    ssl = True


class TestUpstreamProxy(TBase, tservers.HTTPUpstreamProxyTest):
    pass


class TestClientPlayback:
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

    @pytest.mark.asyncio
    async def test_playback(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp) as ctx:
            assert cp.count() == 0
            f = tflow.tflow(resp=True)
            cp.start_replay([f])
            assert cp.count() == 1

            cp.stop_replay()
            assert cp.count() == 0

            f.live = True
            cp.start_replay([f])
            assert cp.count() == 0
            await ctx.master.await_log("live")

    def test_http2(self):
        cp = clientplayback.ClientPlayback()
        with taddons.context(cp):
            req = tutils.treq(
                headers = net_http.Headers(
                    (
                        (b":authority", b"foo"),
                        (b"header", b"qvalue"),
                        (b"content-length", b"7")
                    )
                )
            )
            f = tflow.tflow(req=req)
            f.request.http_version = "HTTP/2.0"
            cp.start_replay([f])
            assert f.request.http_version == "HTTP/1.1"
            assert ":authority" not in f.request.headers
