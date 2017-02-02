import io
import pytest

from mitmproxy.test import tflow
from mitmproxy.net.http import Headers
import mitmproxy.io
from mitmproxy import flowfilter, options
from mitmproxy.contrib import tnetstring
from mitmproxy.exceptions import FlowReadException, Kill
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import connections
from mitmproxy.proxy import ProxyConfig
from mitmproxy.proxy.server import DummyServer
from mitmproxy import master
from . import tservers


class TestHTTPFlow:

    def test_copy(self):
        f = tflow.tflow(resp=True)
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert f is not f2
        assert f.request.get_state() == f2.request.get_state()
        assert f.request is not f2.request
        assert f.request.headers == f2.request.headers
        assert f.request.headers is not f2.request.headers
        assert f.response.get_state() == f2.response.get_state()
        assert f.response is not f2.response

        f = tflow.tflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.request is not f2.request
        assert f.request.headers == f2.request.headers
        assert f.request.headers is not f2.request.headers
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.tflow(resp=True)
        assert not flowfilter.match("~b test", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b test", f)

        f = tflow.tflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_backup(self):
        f = tflow.tflow()
        f.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        f.request.content = b"foo"
        assert not f.modified()
        f.backup()
        f.request.content = b"bar"
        assert f.modified()
        f.revert()
        assert f.request.content == b"foo"

    def test_backup_idempotence(self):
        f = tflow.tflow(resp=True)
        f.backup()
        f.revert()
        f.backup()
        f.revert()

    def test_getset_state(self):
        f = tflow.tflow(resp=True)
        state = f.get_state()
        assert f.get_state() == http.HTTPFlow.from_state(
            state).get_state()

        f.response = None
        f.error = flow.Error("error")
        state = f.get_state()
        assert f.get_state() == http.HTTPFlow.from_state(
            state).get_state()

        f2 = f.copy()
        f2.id = f.id  # copy creates a different uuid
        assert f.get_state() == f2.get_state()
        assert not f == f2
        f2.error = flow.Error("e2")
        assert not f == f2
        f.set_state(f2.get_state())
        assert f.get_state() == f2.get_state()

    def test_kill(self):
        f = tflow.tflow()
        f.reply.handle()
        f.intercept()
        assert f.killable
        f.kill()
        assert not f.killable
        assert f.reply.value == Kill

    def test_resume(self):
        f = tflow.tflow()
        f.reply.handle()
        f.intercept()
        assert f.reply.state == "taken"
        f.resume()
        assert f.reply.state == "committed"

    def test_replace_unicode(self):
        f = tflow.tflow(resp=True)
        f.response.content = b"\xc2foo"
        f.replace(b"foo", u"bar")

    def test_replace_no_content(self):
        f = tflow.tflow()
        f.request.content = None
        assert f.replace("foo", "bar") == 0

    def test_replace(self):
        f = tflow.tflow(resp=True)
        f.request.headers["foo"] = "foo"
        f.request.content = b"afoob"

        f.response.headers["foo"] = "foo"
        f.response.content = b"afoob"

        assert f.replace("foo", "bar") == 6

        assert f.request.headers["bar"] == "bar"
        assert f.request.content == b"abarb"
        assert f.response.headers["bar"] == "bar"
        assert f.response.content == b"abarb"

    def test_replace_encoded(self):
        f = tflow.tflow(resp=True)
        f.request.content = b"afoob"
        f.request.encode("gzip")
        f.response.content = b"afoob"
        f.response.encode("gzip")

        f.replace("foo", "bar")

        assert f.request.raw_content != b"abarb"
        f.request.decode()
        assert f.request.raw_content == b"abarb"

        assert f.response.raw_content != b"abarb"
        f.response.decode()
        assert f.response.raw_content == b"abarb"


class TestTCPFlow:

    def test_match(self):
        f = tflow.ttcpflow()
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b nonexistent", f)

        f = tflow.ttcpflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)


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
            mode="reverse",
            upstream_server="https://use-this-domain"
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
        with pytest.raises(FlowReadException):
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
        with pytest.raises("version"):
            list(r.stream())


class TestFlowMaster:

    def test_replay(self):
        fm = master.Master(None, DummyServer())
        f = tflow.tflow(resp=True)
        f.request.content = None
        with pytest.raises("missing"):
            fm.replay_request(f)

        f.intercepted = True
        with pytest.raises("intercepted"):
            fm.replay_request(f)

        f.live = True
        with pytest.raises("live"):
            fm.replay_request(f)

    def test_create_flow(self):
        fm = master.Master(None, DummyServer())
        assert fm.create_request("GET", "http", "example.com", 80, "/")

    def test_new_request(self):
        fm = master.Master(None, DummyServer())
        f = tflow.tflow(resp=True)
        f.request.content = None
        with pytest.raises("missing"):
            fm.new_request(f.request.method, f)

        f.intercepted = True
        with pytest.raises("intercepted"):
            fm.new_request(f.request.method, f)

        f.live = True
        with pytest.raises("live"):
            fm.new_request(f.request.method, f)

    def test_all(self):
        s = tservers.TestState()
        fm = master.Master(None, DummyServer())
        fm.addons.add(s)
        f = tflow.tflow(req=None)
        fm.clientconnect(f.client_conn)
        f.request = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())
        fm.request(f)
        assert s.flow_count() == 1

        f.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        fm.response(f)
        assert s.flow_count() == 1

        fm.clientdisconnect(f.client_conn)

        f.error = flow.Error("msg")
        fm.error(f)

        fm.shutdown()


class TestRequest:

    def test_simple(self):
        f = tflow.tflow()
        r = f.request
        u = r.url
        r.url = u
        with pytest.raises(ValueError):
            setattr(r, "url", "")
        assert r.url == u
        r2 = r.copy()
        assert r.get_state() == r2.get_state()

    def test_get_url(self):
        r = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())

        assert r.url == "http://address:22/path"

        r.scheme = "https"
        assert r.url == "https://address:22/path"

        r.host = "host"
        r.port = 42
        assert r.url == "https://host:42/path"

        r.host = "address"
        r.port = 22
        assert r.url == "https://address:22/path"

        assert r.pretty_url == "https://address:22/path"
        r.headers["Host"] = "foo.com:22"
        assert r.url == "https://address:22/path"
        assert r.pretty_url == "https://foo.com:22/path"

    def test_replace(self):
        r = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())
        r.path = "path/foo"
        r.headers["Foo"] = "fOo"
        r.content = b"afoob"
        assert r.replace("foo(?i)", "boo") == 4
        assert r.path == "path/boo"
        assert b"foo" not in r.content
        assert r.headers["boo"] == "boo"

    def test_constrain_encoding(self):
        r = http.HTTPRequest.wrap(mitmproxy.test.tutils.treq())
        r.headers["accept-encoding"] = "gzip, oink"
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

        r.headers.set_all("accept-encoding", ["gzip", "oink"])
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

    def test_get_content_type(self):
        resp = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


class TestResponse:

    def test_simple(self):
        f = tflow.tflow(resp=True)
        resp = f.response
        resp2 = resp.copy()
        assert resp2.get_state() == resp.get_state()

    def test_replace(self):
        r = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        r.headers["Foo"] = "fOo"
        r.content = b"afoob"
        assert r.replace("foo(?i)", "boo") == 3
        assert b"foo" not in r.content
        assert r.headers["boo"] == "boo"

    def test_get_content_type(self):
        resp = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


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


class TestClientConnection:
    def test_state(self):
        c = tflow.tclient_conn()
        assert connections.ClientConnection.from_state(c.get_state()).get_state() == \
            c.get_state()

        c2 = tflow.tclient_conn()
        c2.address.address = (c2.address.host, 4242)
        assert not c == c2

        c2.timestamp_start = 42
        c.set_state(c2.get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3.get_state() == c.get_state()

        assert str(c)
