import io
from unittest import mock
import pytest

from mitmproxy.test import tflow, tutils, taddons
import mitmproxy.io
from mitmproxy import flowfilter
from mitmproxy import options
from mitmproxy.io import tnetstring
from mitmproxy.exceptions import FlowReadException, ReplayException
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.net import http as net_http
from mitmproxy import master
from . import tservers


class TestSerialize:

    def test_roundtrip(self):
        sio = io.BytesIO()
        f = tflow.tflow()
        f.marked = True
        f.request.content = bytes(range(256))
        w = mitmproxy.io.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = mitmproxy.io.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1

        f2 = l[0]
        assert f2.get_state() == f.get_state()
        assert f2.request == f.request
        assert f2.marked

    def test_filter(self):
        sio = io.BytesIO()
        flt = flowfilter.parse("~c 200")
        w = mitmproxy.io.FilteredFlowWriter(sio, flt)

        f = tflow.tflow(resp=True)
        f.response.status_code = 200
        w.add(f)

        f = tflow.tflow(resp=True)
        f.response.status_code = 201
        w.add(f)

        sio.seek(0)
        r = mitmproxy.io.FlowReader(sio)
        assert len(list(r.stream()))

    def test_error(self):
        sio = io.BytesIO()
        sio.write(b"bogus")
        sio.seek(0)
        r = mitmproxy.io.FlowReader(sio)
        with pytest.raises(FlowReadException, match='Invalid data format'):
            list(r.stream())

        sio = io.BytesIO()
        f = tflow.tdummyflow()
        w = mitmproxy.io.FlowWriter(sio)
        w.add(f)
        sio.seek(0)
        r = mitmproxy.io.FlowReader(sio)
        with pytest.raises(FlowReadException, match='Unknown flow type'):
            list(r.stream())

        f = FlowReadException("foo")
        assert str(f) == "foo"

    def test_versioncheck(self):
        f = tflow.tflow()
        d = f.get_state()
        d["version"] = (0, 0)
        sio = io.BytesIO()
        tnetstring.dump(d, sio)
        sio.seek(0)

        r = mitmproxy.io.FlowReader(sio)
        with pytest.raises(Exception, match="version"):
            list(r.stream())

    def test_copy(self):
        """
        _backup may be shared across instances. That should not raise errors.
        """
        f = tflow.tflow()
        f.backup()
        f.request.path = "/foo"
        f2 = f.copy()
        f2.revert()
        f.revert()


class TestFlowMaster:
    @pytest.mark.asyncio
    async def test_load_http_flow_reverse(self):
        opts = options.Options(
            mode="reverse:https://use-this-domain"
        )
        s = tservers.TestState()
        with taddons.context(s, options=opts) as ctx:
            f = tflow.tflow(resp=True)
            await ctx.master.load_flow(f)
            assert s.flows[0].request.host == "use-this-domain"

    @pytest.mark.asyncio
    async def test_load_websocket_flow(self):
        opts = options.Options(
            mode="reverse:https://use-this-domain"
        )
        s = tservers.TestState()
        with taddons.context(s, options=opts) as ctx:
            f = tflow.twebsocketflow()
            await ctx.master.load_flow(f.handshake_flow)
            await ctx.master.load_flow(f)
            assert s.flows[0].request.host == "use-this-domain"
            assert s.flows[1].handshake_flow == f.handshake_flow
            assert len(s.flows[1].messages) == len(f.messages)

    def test_replay(self):
        opts = options.Options()
        fm = master.Master(opts)
        f = tflow.tflow(resp=True)
        f.request.content = None
        with pytest.raises(ReplayException, match="missing"):
            fm.replay_request(f)

        f.request = None
        with pytest.raises(ReplayException, match="request"):
            fm.replay_request(f)

        f.intercepted = True
        with pytest.raises(ReplayException, match="intercepted"):
            fm.replay_request(f)

        f.live = True
        with pytest.raises(ReplayException, match="live"):
            fm.replay_request(f)

        req = tutils.treq(headers=net_http.Headers(((b":authority", b"foo"), (b"header", b"qvalue"), (b"content-length", b"7"))))
        f = tflow.tflow(req=req)
        f.request.http_version = "HTTP/2.0"
        with mock.patch('mitmproxy.proxy.protocol.http_replay.RequestReplayThread.run'):
            rt = fm.replay_request(f)
            assert rt.f.request.http_version == "HTTP/1.1"
            assert ":authority" not in rt.f.request.headers

    @pytest.mark.asyncio
    async def test_all(self):
        opts = options.Options(
            mode="reverse:https://use-this-domain"
        )
        s = tservers.TestState()
        with taddons.context(s, options=opts) as ctx:
            f = tflow.tflow(req=None)
            await ctx.master.addons.handle_lifecycle("clientconnect", f.client_conn)
            f.request = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())
            await ctx.master.addons.handle_lifecycle("request", f)
            assert len(s.flows) == 1

            f.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
            await ctx.master.addons.handle_lifecycle("response", f)
            assert len(s.flows) == 1

            await ctx.master.addons.handle_lifecycle("clientdisconnect", f.client_conn)

            f.error = flow.Error("msg")
            await ctx.master.addons.handle_lifecycle("error", f)


class TestError:

    def test_getset_state(self):
        e = flow.Error("Error")
        state = e.get_state()
        assert flow.Error.from_state(state).get_state() == e.get_state()

        assert e.copy()

        e2 = flow.Error("bar")
        assert not e == e2
        e.set_state(e2.get_state())
        assert e.get_state() == e2.get_state()

        e3 = e.copy()
        assert e3.get_state() == e.get_state()

    def test_repr(self):
        e = flow.Error("yay")
        assert repr(e)
        assert str(e)
