from io import BytesIO
from netlib.exceptions import HttpSyntaxException

from netlib.http import http1
from netlib.tutils import treq, raises
import tutils
import tservers


class TestHTTPResponse:
    def test_read_from_stringio(self):
        s = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 7\r\n"
            b"\r\n"
            b"content\r\n"
            b"HTTP/1.1 204 OK\r\n"
            b"\r\n"
        )
        rfile = BytesIO(s)
        r = http1.read_response(rfile, treq())
        assert r.status_code == 200
        assert r.content == b"content"
        assert http1.read_response(rfile, treq()).status_code == 204

        rfile = BytesIO(s)
        # HEAD must not have content by spec. We should leave it on the pipe.
        r = http1.read_response(rfile, treq(method=b"HEAD"))
        assert r.status_code == 200
        assert r.content == b""

        with raises(HttpSyntaxException):
            http1.read_response(rfile, treq())


class TestHTTPFlow(object):
    def test_repr(self):
        f = tutils.tflow(resp=True, err=True)
        assert repr(f)


class TestInvalidRequests(tservers.HTTPProxTest):
    ssl = True

    def test_double_connect(self):
        p = self.pathoc()
        r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert "Invalid HTTP request form" in r.body

    def test_relative_request(self):
        p = self.pathoc_raw()
        p.connect()
        r = p.request("get:/p/200")
        assert r.status_code == 400
        assert "Invalid HTTP request form" in r.body
