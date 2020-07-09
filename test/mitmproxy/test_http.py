import pytest

from mitmproxy.test import tflow
from mitmproxy.net.http import Headers
import mitmproxy.io
from mitmproxy import flowfilter
from mitmproxy.exceptions import Kill, ControlException
from mitmproxy import flow
from mitmproxy import http


class TestHTTPRequest:

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
        assert hash(r)

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


class TestHTTPResponse:

    def test_simple(self):
        f = tflow.tflow(resp=True)
        resp = f.response
        resp2 = resp.copy()
        assert resp2.get_state() == resp.get_state()

    def test_get_content_type(self):
        resp = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


class TestHTTPFlow:

    def test_copy(self):
        f = tflow.tflow(resp=True)
        assert repr(f)
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
        f2.backup()
        f2.intercept()  # to change the state
        f.set_state(f2.get_state())
        assert f.get_state() == f2.get_state()

    def test_kill(self):
        f = tflow.tflow()
        with pytest.raises(ControlException):
            f.intercept()
            f.resume()
            f.kill()

        f = tflow.tflow()
        f.intercept()
        assert f.killable
        f.kill()
        assert not f.killable
        assert f.reply.value == Kill

    def test_intercept(self):
        f = tflow.tflow()
        f.intercept()
        assert f.reply.state == "taken"
        f.intercept()
        assert f.reply.state == "taken"

    def test_resume(self):
        f = tflow.tflow()
        f.intercept()
        assert f.reply.state == "taken"
        f.resume()
        assert f.reply.state == "committed"

    def test_resume_duplicated(self):
        f = tflow.tflow()
        f.intercept()
        f2 = f.copy()
        assert f.intercepted is f2.intercepted is True
        f.resume()
        f2.resume()
        assert f.intercepted is f2.intercepted is False

    def test_timestamp_start(self):
        f = tflow.tflow()
        assert f.timestamp_start == f.request.timestamp_start


def test_make_error_response():
    resp = http.make_error_response(543, 'foobar', Headers())
    assert resp


def test_make_connect_request():
    req = http.make_connect_request(('invalidhost', 1234))
    assert req.first_line_format == 'authority'
    assert req.method == 'CONNECT'
    assert req.http_version == 'HTTP/1.1'


def test_make_connect_response():
    resp = http.make_connect_response('foobar')
    assert resp.http_version == 'foobar'
    assert resp.status_code == 200


def test_expect_continue_response():
    assert http.expect_continue_response.http_version == 'HTTP/1.1'
    assert http.expect_continue_response.status_code == 100
