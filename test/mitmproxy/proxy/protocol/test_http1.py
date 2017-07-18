from unittest import mock
import pytest

from mitmproxy.test import tflow
from mitmproxy.net.http import http1
from mitmproxy.net.tcp import TCPClient
from mitmproxy.test.tutils import treq
from ... import tservers


class TestHTTPFlow:

    def test_repr(self):
        f = tflow.tflow(resp=True, err=True)
        assert repr(f)


class TestInvalidRequests(tservers.HTTPProxyTest):
    ssl = True

    def test_double_connect(self):
        p = self.pathoc()
        with p.connect():
            r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert b"Unexpected CONNECT" in r.content

    def test_relative_request(self):
        p = self.pathoc_raw()
        with p.connect():
            r = p.request("get:/p/200")
        assert r.status_code == 400
        assert b"Invalid HTTP request form" in r.content


class TestProxyMisconfiguration(tservers.TransparentProxyTest):

    def test_absolute_request(self):
        p = self.pathoc()
        with p.connect():
            r = p.request("get:'http://localhost:%d/p/200'" % self.server.port)
        assert r.status_code == 400
        assert b"misconfiguration" in r.content


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
        client.close()


class TestHeadContentLength(tservers.HTTPProxyTest):

    def test_head_content_length(self):
        p = self.pathoc()
        with p.connect():
            resp = p.request(
                """head:'%s/p/200:h"Content-Length"="42"'""" % self.server.urlbase
            )
        assert resp.headers["Content-Length"] == "42"


class TestStreaming(tservers.HTTPProxyTest):

    @pytest.mark.parametrize('streaming', [True, False])
    def test_streaming(self, streaming):

        class Stream:
            def requestheaders(self, f):
                f.request.stream = streaming

            def responseheaders(self, f):
                f.response.stream = streaming

        def assert_write(self, v):
            if streaming:
                assert len(v) <= 4096
            return self.o.write(v)

        self.master.addons.add(Stream())
        p = self.pathoc()
        with p.connect():
            with mock.patch("mitmproxy.net.tcp.Writer.write", side_effect=assert_write, autospec=True):
                # response with 10000 bytes
                r = p.request("post:'%s/p/200:b@10000'" % self.server.urlbase)
                assert len(r.content) == 10000

                # request with 10000 bytes
                assert p.request("post:'%s/p/200':b@10000" % self.server.urlbase)
