import cStringIO
from cStringIO import StringIO

from mock import MagicMock

from libmproxy.protocol.http import *
import netlib.http
from netlib.http import http1
from netlib.http.semantics import CONTENT_MISSING

import tutils
import tservers

def mock_protocol(data=''):
    rfile = cStringIO.StringIO(data)
    wfile = cStringIO.StringIO()
    return http1.HTTP1Protocol(rfile=rfile, wfile=wfile)


class TestHTTPResponse:
    def test_read_from_stringio(self):
        s = "HTTP/1.1 200 OK\r\n" \
             "Content-Length: 7\r\n" \
             "\r\n"\
             "content\r\n" \
             "HTTP/1.1 204 OK\r\n" \
             "\r\n"

        protocol = mock_protocol(s)
        r = HTTPResponse.from_protocol(protocol, "GET")
        assert r.status_code == 200
        assert r.content == "content"
        assert HTTPResponse.from_protocol(protocol, "GET").status_code == 204

        protocol = mock_protocol(s)
        # HEAD must not have content by spec. We should leave it on the pipe.
        r = HTTPResponse.from_protocol(protocol, "HEAD")
        assert r.status_code == 200
        assert r.content == ""
        tutils.raises(
            "Invalid server response: 'content",
            HTTPResponse.from_protocol, protocol, "GET"
        )


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
