import io
import pytest

from mitmproxy.test import tflow
import mitmproxy.io
from mitmproxy import flowfilter, options
from mitmproxy.contrib import tnetstring
from mitmproxy.exceptions import FlowReadException
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.proxy import ProxyConfig
from mitmproxy.proxy.server import DummyServer
from mitmproxy import master
from . import tservers


class TestSerialize:

    def _treader(self):
        sio = io.BytesIO()
        w = mitmproxy.io.FlowWriter(sio)
        for i in range(3):
            f = tflow.tflow(resp=True)
            w.add(f)
        for i in range(3):
            f = tflow.tflow(err=True)
            w.add(f)
        f = tflow.ttcpflow()
        w.add(f)
        f = tflow.ttcpflow(err=True)
        w.add(f)

        sio.seek(0)
        return mitmproxy.io.FlowReader(sio)

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

    def test_load_flows(self):
        r = self._treader()
        s = tservers.TestState()
        fm = master.Master(None, DummyServer())
        fm.addons.add(s)
        fm.load_flows(r)
        assert len(s.flows) == 6

    def test_load_flows_reverse(self):
        r = self._treader()
        s = tservers.TestState()
        opts = options.Options(
            mode="reverse:https://use-this-domain"
        )
        conf = ProxyConfig(opts)
        fm = master.Master(opts, DummyServer(conf))
        fm.addons.add(s)
        fm.load_flows(r)
        assert s.flows[0].request.host == "use-this-domain"

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


class TestFlowMaster:

    def test_replay(self):
        fm = master.Master(None, DummyServer())
        f = tflow.tflow(resp=True)
        f.request.content = None
        with pytest.raises(Exception, match="missing"):
            fm.replay_request(f)

        f.intercepted = True
        with pytest.raises(Exception, match="intercepted"):
            fm.replay_request(f)

        f.live = True
        with pytest.raises(Exception, match="live"):
            fm.replay_request(f)

    def test_create_flow(self):
        fm = master.Master(None, DummyServer())
        assert fm.create_request("GET", "http://example.com/")

    def test_all(self):
        s = tservers.TestState()
        fm = master.Master(None, DummyServer())
        fm.addons.add(s)
        f = tflow.tflow(req=None)
        fm.clientconnect(f.client_conn)
        f.request = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())
        fm.request(f)
        assert len(s.flows) == 1

        f.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        fm.response(f)
        assert len(s.flows) == 1

        fm.clientdisconnect(f.client_conn)

        f.error = flow.Error("msg")
        fm.error(f)

        fm.shutdown()


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
