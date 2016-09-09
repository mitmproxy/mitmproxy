from __future__ import (absolute_import, print_function, division)

from netlib.http import http1
from netlib.tcp import TCPClient
from netlib.tutils import treq
from .. import tutils, tservers


class TestHTTPFlow(object):

    def test_repr(self):
        f = tutils.tflow(resp=True, err=True)
        assert repr(f)


class TestInvalidRequests(tservers.HTTPProxyTest):
    ssl = True

    def test_double_connect(self):
        p = self.pathoc()
        with p.connect():
            r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert b"Invalid HTTP request form" in r.content

    def test_relative_request(self):
        p = self.pathoc_raw()
        with p.connect():
            r = p.request("get:/p/200")
        assert r.status_code == 400
        assert b"Invalid HTTP request form" in r.content


class TestExpectHeader(tservers.HTTPProxyTest):

    def test_simple(self):
        client = TCPClient(("127.0.0.1", self.proxy.port))
        client.connect()

        # call pathod server, wait a second to complete the request
        client.wfile.write(
            b"POST http://localhost:%d/p/200 HTTP/1.1\r\n"
            b"Expect: 100-continue\r\n"
            b"Content-Length: 16\r\n"
            b"\r\n" % self.server.port
        )
        client.wfile.flush()

        assert client.rfile.readline() == b"HTTP/1.1 100 Continue\r\n"
        assert client.rfile.readline() == b"\r\n"

        client.wfile.write(b"0123456789abcdef\r\n")
        client.wfile.flush()

        resp = http1.read_response(client.rfile, treq())
        assert resp.status_code == 200

        client.finish()


class TestHeadContentLength(tservers.HTTPProxyTest):

    def test_head_content_length(self):
        p = self.pathoc()
        with p.connect():
            resp = p.request(
                """head:'%s/p/200:h"Content-Length"="42"'""" % self.server.urlbase
            )
        assert resp.headers["Content-Length"] == "42"
