from six.moves import queue
import time
import os.path
from six.moves import cStringIO as StringIO
import email.utils

import mock

import netlib.utils
from netlib import odict
from netlib.http import Headers
from mitmproxy import filt, controller, tnetstring, flow
from mitmproxy.models import Error
from mitmproxy.models import Flow
from mitmproxy.models import HTTPFlow
from mitmproxy.models import HTTPRequest
from mitmproxy.models import HTTPResponse
from mitmproxy.proxy.config import HostMatcher
from mitmproxy.proxy import ProxyConfig
from mitmproxy.proxy.server import DummyServer
from mitmproxy.models.connections import ClientConnection
from . import tutils


def test_app_registry():
    ar = flow.AppRegistry()
    ar.add("foo", "domain", 80)

    r = HTTPRequest.wrap(netlib.tutils.treq())
    r.host = "domain"
    r.port = 80
    assert ar.get(r)

    r.port = 81
    assert not ar.get(r)

    r = HTTPRequest.wrap(netlib.tutils.treq())
    r.host = "domain2"
    r.port = 80
    assert not ar.get(r)
    r.headers["host"] = "domain"
    assert ar.get(r)


class TestStickyCookieState:

    def _response(self, cookie, host):
        s = flow.StickyCookieState(filt.parse(".*"))
        f = tutils.tflow(req=netlib.tutils.treq(host=host, port=80), resp=True)
        f.response.headers["Set-Cookie"] = cookie
        s.handle_response(f)
        return s, f

    def test_domain_match(self):
        s = flow.StickyCookieState(filt.parse(".*"))
        assert s.domain_match("www.google.com", ".google.com")
        assert s.domain_match("google.com", ".google.com")

    def test_handle_response(self):
        c = "SSID=mooo; domain=.google.com, FOO=bar; Domain=.google.com; Path=/; "\
            "Expires=Wed, 13-Jan-2021 22:23:01 GMT; Secure; "

        s, f = self._response(c, "host")
        assert not s.jar.keys()

        s, f = self._response(c, "www.google.com")
        assert s.jar.keys()

        s, f = self._response("SSID=mooo", "www.google.com")
        assert s.jar.keys()[0] == ('www.google.com', 80, '/')

    def test_handle_request(self):
        s, f = self._response("SSID=mooo", "www.google.com")
        assert "cookie" not in f.request.headers
        s.handle_request(f)
        assert "cookie" in f.request.headers


class TestStickyAuthState:

    def test_handle_response(self):
        s = flow.StickyAuthState(filt.parse(".*"))
        f = tutils.tflow(resp=True)
        f.request.headers["authorization"] = "foo"
        s.handle_request(f)
        assert "address" in s.hosts

        f = tutils.tflow(resp=True)
        s.handle_request(f)
        assert f.request.headers["authorization"] == "foo"


class TestClientPlaybackState:

    def test_tick(self):
        first = tutils.tflow()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.start_client_playback([first, tutils.tflow()], True)
        c = fm.client_playback
        c.testing = True

        assert not c.done()
        assert not s.flow_count()
        assert c.count() == 2
        c.tick(fm)
        assert s.flow_count()
        assert c.count() == 1

        c.tick(fm)
        assert c.count() == 1

        c.clear(c.current)
        c.tick(fm)
        assert c.count() == 0
        c.clear(c.current)
        assert c.done()

        q = queue.Queue()
        fm.state.clear()
        fm.tick(q, timeout=0)

        fm.stop_client_playback()
        assert not fm.client_playback


class TestServerPlaybackState:

    def test_hash(self):
        s = flow.ServerPlaybackState(
            None,
            [],
            False,
            False,
            None,
            False,
            None,
            False)
        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

        r.request.path = "path?blank_value"
        r2.request.path = "path?"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = flow.ServerPlaybackState(
            ["foo"],
            [],
            False,
            False,
            None,
            False,
            None,
            False)
        r = tutils.tflow(resp=True)
        r.request.headers["foo"] = "bar"
        r2 = tutils.tflow(resp=True)
        assert not s._hash(r) == s._hash(r2)
        r2.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.headers["oink"] = "bar"
        assert s._hash(r) == s._hash(r2)

        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)
        assert s._hash(r) == s._hash(r2)

    def test_load(self):
        r = tutils.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tutils.tflow(resp=True)
        r2.request.headers["key"] = "two"

        s = flow.ServerPlaybackState(
            None, [
                r, r2], False, False, None, False, None, False)
        assert s.count() == 2
        assert len(s.fmap.keys()) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == "one"
        assert s.count() == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == "two"
        assert s.count() == 0

        assert not s.next_flow(r)

    def test_load_with_nopop(self):
        r = tutils.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tutils.tflow(resp=True)
        r2.request.headers["key"] = "two"

        s = flow.ServerPlaybackState(
            None, [
                r, r2], False, True, None, False, None, False)

        assert s.count() == 2
        s.next_flow(r)
        assert s.count() == 2

    def test_ignore_params(self):
        s = flow.ServerPlaybackState(
            None, [], False, False, [
                "param1", "param2"], False, None, False)
        r = tutils.tflow(resp=True)
        r.request.path = "/test?param1=1"
        r2 = tutils.tflow(resp=True)
        r2.request.path = "/test"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param1=2"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param2=1"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param3=2"
        assert not s._hash(r) == s._hash(r2)

    def test_ignore_payload_params(self):
        s = flow.ServerPlaybackState(
            None, [], False, False, None, False, [
                "param1", "param2"], False)
        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r.request.content = "paramx=x&param1=1"
        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r2.request.content = "paramx=x&param1=1"
        # same parameters
        assert s._hash(r) == s._hash(r2)
        # ignored parameters !=
        r2.request.content = "paramx=x&param1=2"
        assert s._hash(r) == s._hash(r2)
        # missing parameter
        r2.request.content = "paramx=x"
        assert s._hash(r) == s._hash(r2)
        # ignorable parameter added
        r2.request.content = "paramx=x&param1=2"
        assert s._hash(r) == s._hash(r2)
        # not ignorable parameter changed
        r2.request.content = "paramx=y&param1=1"
        assert not s._hash(r) == s._hash(r2)
        # not ignorable parameter missing
        r2.request.content = "param1=1"
        assert not s._hash(r) == s._hash(r2)

    def test_ignore_payload_params_other_content_type(self):
        s = flow.ServerPlaybackState(
            None, [], False, False, None, False, [
                "param1", "param2"], False)
        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/json"
        r.request.content = '{"param1":"1"}'
        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/json"
        r2.request.content = '{"param1":"1"}'
        # same content
        assert s._hash(r) == s._hash(r2)
        # distint content (note only x-www-form-urlencoded payload is analysed)
        r2.request.content = '{"param1":"2"}'
        assert not s._hash(r) == s._hash(r2)

    def test_ignore_payload_wins_over_params(self):
        # NOTE: parameters are mutually exclusive in options
        s = flow.ServerPlaybackState(
            None, [], False, False, None, True, [
                "param1", "param2"], False)
        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r.request.content = "paramx=y"
        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r2.request.content = "paramx=x"
        # same parameters
        assert s._hash(r) == s._hash(r2)

    def test_ignore_content(self):
        s = flow.ServerPlaybackState(
            None,
            [],
            False,
            False,
            None,
            False,
            None,
            False)
        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)

        r.request.content = "foo"
        r2.request.content = "foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = "bar"
        assert not s._hash(r) == s._hash(r2)

        # now ignoring content
        s = flow.ServerPlaybackState(
            None,
            [],
            False,
            False,
            None,
            True,
            None,
            False)
        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)
        r.request.content = "foo"
        r2.request.content = "foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = "bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = ""
        assert s._hash(r) == s._hash(r2)
        r2.request.content = None
        assert s._hash(r) == s._hash(r2)

    def test_ignore_host(self):
        s = flow.ServerPlaybackState(
            None,
            [],
            False,
            False,
            None,
            False,
            None,
            True)
        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)

        r.request.host = "address"
        r2.request.host = "address"
        assert s._hash(r) == s._hash(r2)
        r2.request.host = "wrong_address"
        assert s._hash(r) == s._hash(r2)


class TestFlow(object):

    def test_copy(self):
        f = tutils.tflow(resp=True)
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert not f is f2
        assert f.request.get_state() == f2.request.get_state()
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.response.get_state() == f2.response.get_state()
        assert not f.response is f2.response

        f = tutils.tflow(err=True)
        f2 = f.copy()
        assert not f is f2
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.error.get_state() == f2.error.get_state()
        assert not f.error is f2.error

    def test_match(self):
        f = tutils.tflow(resp=True)
        assert not f.match("~b test")
        assert f.match(None)
        assert not f.match("~b test")

        f = tutils.tflow(err=True)
        assert f.match("~e")

        tutils.raises(ValueError, f.match, "~")

    def test_backup(self):
        f = tutils.tflow()
        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        f.request.content = "foo"
        assert not f.modified()
        f.backup()
        f.request.content = "bar"
        assert f.modified()
        f.revert()
        assert f.request.content == "foo"

    def test_backup_idempotence(self):
        f = tutils.tflow(resp=True)
        f.backup()
        f.revert()
        f.backup()
        f.revert()

    def test_getset_state(self):
        f = tutils.tflow(resp=True)
        state = f.get_state()
        assert f.get_state() == HTTPFlow.from_state(
            state).get_state()

        f.response = None
        f.error = Error("error")
        state = f.get_state()
        assert f.get_state() == HTTPFlow.from_state(
            state).get_state()

        f2 = f.copy()
        f2.id = f.id  # copy creates a different uuid
        assert f.get_state() == f2.get_state()
        assert not f == f2
        f2.error = Error("e2")
        assert not f == f2
        f.set_state(f2.get_state())
        assert f.get_state() == f2.get_state()

    def test_kill(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow()
        f.intercept(mock.Mock())
        assert not f.reply.acked
        f.kill(fm)
        assert f.reply.acked

    def test_killall(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        f = tutils.tflow()
        fm.handle_request(f)

        f = tutils.tflow()
        fm.handle_request(f)

        for i in s.view:
            assert not i.reply.acked
        s.killall(fm)
        for i in s.view:
            assert i.reply.acked

    def test_accept_intercept(self):
        f = tutils.tflow()

        f.intercept(mock.Mock())
        assert not f.reply.acked
        f.accept_intercept(mock.Mock())
        assert f.reply.acked

    def test_replace_unicode(self):
        f = tutils.tflow(resp=True)
        f.response.content = "\xc2foo"
        f.replace("foo", u"bar")

    def test_replace_no_content(self):
        f = tutils.tflow()
        f.request.content = None
        assert f.replace("foo", "bar") == 0

    def test_replace(self):
        f = tutils.tflow(resp=True)
        f.request.headers["foo"] = "foo"
        f.request.content = "afoob"

        f.response.headers["foo"] = "foo"
        f.response.content = "afoob"

        assert f.replace("foo", "bar") == 6

        assert f.request.headers["bar"] == "bar"
        assert f.request.content == "abarb"
        assert f.response.headers["bar"] == "bar"
        assert f.response.content == "abarb"

    def test_replace_encoded(self):
        f = tutils.tflow(resp=True)
        f.request.content = "afoob"
        f.request.encode("gzip")
        f.response.content = "afoob"
        f.response.encode("gzip")

        f.replace("foo", "bar")

        assert f.request.content != "abarb"
        f.request.decode()
        assert f.request.content == "abarb"

        assert f.response.content != "abarb"
        f.response.decode()
        assert f.response.content == "abarb"


class TestState:

    def test_backup(self):
        c = flow.State()
        f = tutils.tflow()
        c.add_flow(f)
        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = flow.State()
        f = tutils.tflow()
        c.add_flow(f)
        assert f
        assert c.flow_count() == 1
        assert c.active_flow_count() == 1

        newf = tutils.tflow()
        assert c.add_flow(newf)
        assert c.active_flow_count() == 2

        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        assert c.update_flow(f)
        assert c.flow_count() == 2
        assert c.active_flow_count() == 1

        assert not c.update_flow(None)
        assert c.active_flow_count() == 1

        newf.response = HTTPResponse.wrap(netlib.tutils.tresp())
        assert c.update_flow(newf)
        assert c.active_flow_count() == 0

    def test_err(self):
        c = flow.State()
        f = tutils.tflow()
        c.add_flow(f)
        f.error = Error("message")
        assert c.update_flow(f)

        c = flow.State()
        f = tutils.tflow()
        c.add_flow(f)
        c.set_limit("~e")
        assert not c.view
        f.error = tutils.terr()
        assert c.update_flow(f)
        assert c.view

    def test_set_limit(self):
        c = flow.State()

        f = tutils.tflow()
        assert len(c.view) == 0

        c.add_flow(f)
        assert len(c.view) == 1

        c.set_limit("~s")
        assert c.limit_txt == "~s"
        assert len(c.view) == 0
        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        c.update_flow(f)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        f = tutils.tflow()
        c.add_flow(f)
        assert len(c.view) == 2
        c.set_limit("~q")
        assert len(c.view) == 1
        c.set_limit("~s")
        assert len(c.view) == 1

        assert "Invalid" in c.set_limit("~")

    def test_set_intercept(self):
        c = flow.State()
        assert not c.set_intercept("~q")
        assert c.intercept_txt == "~q"
        assert "Invalid" in c.set_intercept("~")
        assert not c.set_intercept(None)
        assert c.intercept_txt is None

    def _add_request(self, state):
        f = tutils.tflow()
        state.add_flow(f)
        return f

    def _add_response(self, state):
        f = tutils.tflow()
        state.add_flow(f)
        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        state.update_flow(f)

    def _add_error(self, state):
        f = tutils.tflow(err=True)
        state.add_flow(f)

    def test_clear(self):
        c = flow.State()
        f = self._add_request(c)
        f.intercepted = True

        c.clear()
        assert c.flow_count() == 0

    def test_dump_flows(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_error(c)

        flows = c.view[:]
        c.clear()

        c.load_flows(flows)
        assert isinstance(c.flows[0], Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all(mock.Mock())


class TestSerialize:

    def _treader(self):
        sio = StringIO()
        w = flow.FlowWriter(sio)
        for i in range(3):
            f = tutils.tflow(resp=True)
            w.add(f)
        for i in range(3):
            f = tutils.tflow(err=True)
            w.add(f)

        sio.seek(0)
        return flow.FlowReader(sio)

    def test_roundtrip(self):
        sio = StringIO()
        f = tutils.tflow()
        f.request.content = "".join(chr(i) for i in range(255))
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1

        f2 = l[0]
        assert f2.get_state() == f.get_state()
        assert f2.request == f.request

    def test_load_flows(self):
        r = self._treader()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_flows(r)
        assert len(s.flows) == 6

    def test_load_flows_reverse(self):
        r = self._treader()
        s = flow.State()
        conf = ProxyConfig(
            mode="reverse",
            upstream_server=("https", ("use-this-domain", 80))
        )
        fm = flow.FlowMaster(DummyServer(conf), s)
        fm.load_flows(r)
        assert s.flows[0].request.host == "use-this-domain"

    def test_filter(self):
        sio = StringIO()
        fl = filt.parse("~c 200")
        w = flow.FilteredFlowWriter(sio, fl)

        f = tutils.tflow(resp=True)
        f.response.status_code = 200
        w.add(f)

        f = tutils.tflow(resp=True)
        f.response.status_code = 201
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        assert len(list(r.stream()))

    def test_error(self):
        sio = StringIO()
        sio.write("bogus")
        sio.seek(0)
        r = flow.FlowReader(sio)
        tutils.raises(flow.FlowReadError, list, r.stream())

        f = flow.FlowReadError("foo")
        assert f.strerror == "foo"

    def test_versioncheck(self):
        f = tutils.tflow()
        d = f.get_state()
        d["version"] = (0, 0)
        sio = StringIO()
        tnetstring.dump(d, sio)
        sio.seek(0)

        r = flow.FlowReader(sio)
        tutils.raises("version", list, r.stream())


class TestFlowMaster:

    def test_load_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.unload_scripts()
        assert fm.load_script("nonexistent")
        assert "ValueError" in fm.load_script(
            tutils.test_data.path("scripts/starterr.py"))
        assert len(fm.scripts) == 0

    def test_getset_ignore(self):
        p = mock.Mock()
        p.config.check_ignore = HostMatcher()
        fm = flow.FlowMaster(p, flow.State())
        assert not fm.get_ignore_filter()
        fm.set_ignore_filter(["^apple\.com:", ":443$"])
        assert fm.get_ignore_filter()

    def test_replay(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow(resp=True)
        f.request.content = None
        assert "missing" in fm.replay_request(f)

        f.intercepted = True
        assert "intercepting" in fm.replay_request(f)

        f.live = True
        assert "live" in fm.replay_request(f, run_scripthooks=True)

    def test_script_reqerr(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/reqerr.py"))
        f = tutils.tflow()
        fm.handle_clientconnect(f.client_conn)
        assert fm.handle_request(f)

    def test_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        f = tutils.tflow(resp=True)

        fm.handle_clientconnect(f.client_conn)
        assert fm.scripts[0].ns["log"][-1] == "clientconnect"
        fm.handle_serverconnect(f.server_conn)
        assert fm.scripts[0].ns["log"][-1] == "serverconnect"
        fm.handle_request(f)
        assert fm.scripts[0].ns["log"][-1] == "request"
        fm.handle_response(f)
        assert fm.scripts[0].ns["log"][-1] == "response"
        # load second script
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        assert len(fm.scripts) == 2
        fm.handle_clientdisconnect(f.server_conn)
        assert fm.scripts[0].ns["log"][-1] == "clientdisconnect"
        assert fm.scripts[1].ns["log"][-1] == "clientdisconnect"

        # unload first script
        fm.unload_scripts()
        assert len(fm.scripts) == 0
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))

        f.error = tutils.terr()
        fm.handle_error(f)
        assert fm.scripts[0].ns["log"][-1] == "error"

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow(resp=True)
        f = fm.load_flow(f)
        assert s.flow_count() == 1
        f2 = fm.duplicate_flow(f)
        assert f2.response
        assert s.flow_count() == 2
        assert s.index(f2) == 1

    def test_create_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert fm.create_request("GET", "http", "example.com", 80, "/")

    def test_all(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.anticache = True
        fm.anticomp = True
        f = tutils.tflow(req=None)
        fm.handle_clientconnect(f.client_conn)
        f.request = HTTPRequest.wrap(netlib.tutils.treq())
        fm.handle_request(f)
        assert s.flow_count() == 1

        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        fm.handle_response(f)
        assert not fm.handle_response(None)
        assert s.flow_count() == 1

        fm.handle_clientdisconnect(f.client_conn)

        f.error = Error("msg")
        f.error.reply = controller.DummyReply()
        fm.handle_error(f)

        fm.load_script(tutils.test_data.path("scripts/a.py"))
        fm.shutdown()

    def test_client_playback(self):
        s = flow.State()

        f = tutils.tflow(resp=True)
        pb = [tutils.tflow(resp=True), f]
        fm = flow.FlowMaster(DummyServer(ProxyConfig()), s)
        assert not fm.start_server_playback(
            pb,
            False,
            [],
            False,
            False,
            None,
            False,
            None,
            False)
        assert not fm.start_client_playback(pb, False)
        fm.client_playback.testing = True

        q = queue.Queue()
        assert not fm.state.flow_count()
        fm.tick(q, 0)
        assert fm.state.flow_count()

        f.error = Error("error")
        fm.handle_error(f)

    def test_server_playback(self):
        s = flow.State()

        f = tutils.tflow()
        f.response = HTTPResponse.wrap(netlib.tutils.tresp(content=f.request))
        pb = [f]

        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        assert not fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(
            pb,
            False,
            [],
            False,
            False,
            None,
            False,
            None,
            False)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(
            pb,
            False,
            [],
            True,
            False,
            None,
            False,
            None,
            False)
        r = tutils.tflow()
        r.request.content = "gibble"
        assert not fm.do_server_playback(r)
        assert fm.do_server_playback(tutils.tflow())

        q = queue.Queue()
        fm.tick(q, 0)
        assert fm.should_exit.is_set()

        fm.stop_server_playback()
        assert not fm.server_playback

    def test_server_playback_kill(self):
        s = flow.State()
        f = tutils.tflow()
        f.response = HTTPResponse.wrap(netlib.tutils.tresp(content=f.request))
        pb = [f]
        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        fm.start_server_playback(
            pb,
            True,
            [],
            False,
            False,
            None,
            False,
            None,
            False)

        f = tutils.tflow()
        f.request.host = "nonexistent"
        fm.process_new_request(f)
        assert "killed" in f.error.msg

    def test_stickycookie(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickycookie("~h")
        fm.set_stickycookie(".*")
        assert fm.stickycookie_state
        fm.set_stickycookie(None)
        assert not fm.stickycookie_state

        fm.set_stickycookie(".*")
        f = tutils.tflow(resp=True)
        f.response.headers["set-cookie"] = "foo=bar"
        fm.handle_request(f)
        fm.handle_response(f)
        assert fm.stickycookie_state.jar
        assert not "cookie" in f.request.headers
        f = f.copy()
        fm.handle_request(f)
        assert f.request.headers["cookie"] == "foo=bar"

    def test_stickyauth(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickyauth("~h")
        fm.set_stickyauth(".*")
        assert fm.stickyauth_state
        fm.set_stickyauth(None)
        assert not fm.stickyauth_state

        fm.set_stickyauth(".*")
        f = tutils.tflow(resp=True)
        f.request.headers["authorization"] = "foo"
        fm.handle_request(f)

        f = tutils.tflow(resp=True)
        assert fm.stickyauth_state.hosts
        assert not "authorization" in f.request.headers
        fm.handle_request(f)
        assert f.request.headers["authorization"] == "foo"

    def test_stream(self):
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")

            def r():
                r = flow.FlowReader(open(p, "rb"))
                return list(r.stream())

            s = flow.State()
            fm = flow.FlowMaster(None, s)
            f = tutils.tflow(resp=True)

            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(f)
            fm.handle_response(f)
            fm.stop_stream()

            assert r()[0].response

            f = tutils.tflow()
            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(f)
            fm.shutdown()

            assert not r()[1].response


class TestRequest:

    def test_simple(self):
        f = tutils.tflow()
        r = f.request
        u = r.url
        r.url = u
        tutils.raises(ValueError, setattr, r, "url", "")
        assert r.url == u
        r2 = r.copy()
        assert r.get_state() == r2.get_state()

    def test_get_url(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())

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

    def test_path_components(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.path = "/"
        assert r.get_path_components() == []
        r.path = "/foo/bar"
        assert r.get_path_components() == ["foo", "bar"]
        q = odict.ODict()
        q["test"] = ["123"]
        r.set_query(q)
        assert r.get_path_components() == ["foo", "bar"]

        r.set_path_components([])
        assert r.get_path_components() == []
        r.set_path_components(["foo"])
        assert r.get_path_components() == ["foo"]
        r.set_path_components(["/oo"])
        assert r.get_path_components() == ["/oo"]
        assert "%2F" in r.path

    def test_getset_form_urlencoded(self):
        d = odict.ODict([("one", "two"), ("three", "four")])
        r = HTTPRequest.wrap(netlib.tutils.treq(content=netlib.utils.urlencode(d.lst)))
        r.headers["content-type"] = "application/x-www-form-urlencoded"
        assert r.get_form_urlencoded() == d

        d = odict.ODict([("x", "y")])
        r.set_form_urlencoded(d)
        assert r.get_form_urlencoded() == d

        r.headers["content-type"] = "foo"
        assert not r.get_form_urlencoded()

    def test_getset_query(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.path = "/foo?x=y&a=b"
        q = r.get_query()
        assert q.lst == [("x", "y"), ("a", "b")]

        r.path = "/"
        q = r.get_query()
        assert not q

        r.path = "/?adsfa"
        q = r.get_query()
        assert q.lst == [("adsfa", "")]

        r.path = "/foo?x=y&a=b"
        assert r.get_query()
        r.set_query(odict.ODict([]))
        assert not r.get_query()
        qv = odict.ODict([("a", "b"), ("c", "d")])
        r.set_query(qv)
        assert r.get_query() == qv

    def test_anticache(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.headers = Headers()
        r.headers["if-modified-since"] = "test"
        r.headers["if-none-match"] = "test"
        r.anticache()
        assert not "if-modified-since" in r.headers
        assert not "if-none-match" in r.headers

    def test_replace(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.path = "path/foo"
        r.headers["Foo"] = "fOo"
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 4
        assert r.path == "path/boo"
        assert not "foo" in r.content
        assert r.headers["boo"] == "boo"

    def test_constrain_encoding(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.headers["accept-encoding"] = "gzip, oink"
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

        r.headers.set_all("accept-encoding", ["gzip", "oink"])
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

    def test_get_decoded_content(self):
        r = HTTPRequest.wrap(netlib.tutils.treq())
        r.content = None
        r.headers["content-encoding"] = "identity"
        assert r.get_decoded_content() is None

        r.content = "falafel"
        r.encode("gzip")
        assert r.get_decoded_content() == "falafel"

    def test_get_content_type(self):
        resp = HTTPResponse.wrap(netlib.tutils.tresp())
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


class TestResponse:

    def test_simple(self):
        f = tutils.tflow(resp=True)
        resp = f.response
        resp2 = resp.copy()
        assert resp2.get_state() == resp.get_state()

    def test_replace(self):
        r = HTTPResponse.wrap(netlib.tutils.tresp())
        r.headers["Foo"] = "fOo"
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 3
        assert not "foo" in r.content
        assert r.headers["boo"] == "boo"

    def test_get_content_type(self):
        resp = HTTPResponse.wrap(netlib.tutils.tresp())
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


class TestError:

    def test_getset_state(self):
        e = Error("Error")
        state = e.get_state()
        assert Error.from_state(state).get_state() == e.get_state()

        assert e.copy()

        e2 = Error("bar")
        assert not e == e2
        e.set_state(e2.get_state())
        assert e.get_state() == e2.get_state()

        e3 = e.copy()
        assert e3.get_state() == e.get_state()


class TestClientConnection:

    def test_state(self):

        c = tutils.tclient_conn()
        assert ClientConnection.from_state(c.get_state()).get_state() ==\
            c.get_state()

        c2 = tutils.tclient_conn()
        c2.address.address = (c2.address.host, 4242)
        assert not c == c2

        c2.timestamp_start = 42
        c.set_state(c2.get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3.get_state() == c.get_state()

        assert str(c)


def test_replacehooks():
    h = flow.ReplaceHooks()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"

    f = tutils.tflow(resp=True)
    f.request.content = "foo"
    f.response.content = "foo"
    h.run(f)
    assert f.response.content == "bar"
    assert f.request.content == "foo"

    f = tutils.tflow()
    h.clear()
    h.add("~q", "foo", "bar")
    f.request.content = "foo"
    h.run(f)
    assert f.request.content == "bar"

    assert not h.add("~", "foo", "bar")
    assert not h.add("foo", "*", "bar")


def test_setheaders():
    h = flow.SetHeaders()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"

    h.clear()
    h.add("~s", "one", "two")
    h.add("~s", "one", "three")
    f = tutils.tflow(resp=True)
    f.request.headers["one"] = "xxx"
    f.response.headers["one"] = "xxx"
    h.run(f)
    assert f.request.headers["one"] == "xxx"
    assert f.response.headers.get_all("one") == ["two", "three"]

    h.clear()
    h.add("~q", "one", "two")
    h.add("~q", "one", "three")
    f = tutils.tflow()
    f.request.headers["one"] = "xxx"
    h.run(f)
    assert f.request.headers.get_all("one") == ["two", "three"]

    assert not h.add("~", "foo", "bar")
