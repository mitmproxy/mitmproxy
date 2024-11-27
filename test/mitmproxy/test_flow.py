import io

import pytest

import mitmproxy.io
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy import options
from mitmproxy.exceptions import FlowReadException
from mitmproxy.io import tnetstring
from mitmproxy.proxy import layers
from mitmproxy.proxy import server_hooks
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class State:
    def __init__(self):
        self.flows = []

    def request(self, f):
        if f not in self.flows:
            self.flows.append(f)

    def response(self, f):
        if f not in self.flows:
            self.flows.append(f)

    def websocket_start(self, f):
        if f not in self.flows:
            self.flows.append(f)


class TestSerialize:
    def test_roundtrip(self):
        sio = io.BytesIO()
        f = tflow.tflow()
        f.marked = ":default:"
        f.marked = True
        f.comment = "test comment"
        f.request.content = bytes(range(256))
        w = mitmproxy.io.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = mitmproxy.io.FlowReader(sio)
        lst = list(r.stream())
        assert len(lst) == 1

        f2 = lst[0]
        assert f2.get_state() == f.get_state()
        assert f2.request.data == f.request.data
        assert f2.marked
        assert f2.comment == "test comment"

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
        buf = io.BytesIO()
        buf.write(b"bogus")
        buf.seek(0)
        r = mitmproxy.io.FlowReader(buf)
        with pytest.raises(FlowReadException, match="Invalid data format"):
            list(r.stream())

        buf = io.BytesIO()
        f = tflow.tdummyflow()
        w = mitmproxy.io.FlowWriter(buf)
        w.add(f)

        buf = io.BytesIO(buf.getvalue().replace(b"dummy", b"nknwn"))
        r = mitmproxy.io.FlowReader(buf)
        with pytest.raises(FlowReadException, match="Unknown flow type"):
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
    async def test_load_http_flow_reverse(self):
        opts = options.Options(mode=["reverse:https://use-this-domain"])
        s = State()
        with taddons.context(s, options=opts) as ctx:
            f = tflow.tflow(resp=True)
            await ctx.master.load_flow(f)
            assert s.flows[0].request.host == "use-this-domain"

    async def test_all(self):
        opts = options.Options(mode=["reverse:https://use-this-domain"])
        s = State()
        with taddons.context(s, options=opts) as ctx:
            f = tflow.tflow(req=None)
            await ctx.master.addons.handle_lifecycle(
                server_hooks.ClientConnectedHook(f.client_conn)
            )
            f.request = mitmproxy.test.tutils.treq()
            await ctx.master.addons.handle_lifecycle(layers.http.HttpRequestHook(f))
            assert len(s.flows) == 1

            f.response = mitmproxy.test.tutils.tresp()
            await ctx.master.addons.handle_lifecycle(layers.http.HttpResponseHook(f))
            assert len(s.flows) == 1

            await ctx.master.addons.handle_lifecycle(
                server_hooks.ClientDisconnectedHook(f.client_conn)
            )

            f.error = flow.Error("msg")
            await ctx.master.addons.handle_lifecycle(layers.http.HttpErrorHook(f))


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
