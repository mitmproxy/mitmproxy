import io
from unittest.mock import Mock
import pytest

from mitmproxy.net import http
from mitmproxy.net.http import http1
from mitmproxy import exceptions

from pathod import pathoc, language
from pathod.protocols.http2 import HTTP2StateProtocol

from mitmproxy.test import tutils
from . import tservers


def test_response():
    r = http.Response(b"HTTP/1.1", 200, b"Message", {}, None, None)
    assert repr(r)


class PathocTestDaemon(tservers.DaemonTests):
    def tval(self, requests, timeout=None, showssl=False, **kwargs):
        s = io.StringIO()
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            ssl=self.ssl,
            fp=s,
            **kwargs
        )
        with c.connect(showssl=showssl, fp=s):
            if timeout:
                c.settimeout(timeout)
            for i in requests:
                r = next(language.parse_pathoc(i))
                if kwargs.get("explain"):
                    r = r.freeze(language.Settings())
                try:
                    c.request(r)
                except exceptions.NetlibException:
                    pass
        self.d.wait_for_silence()
        return s.getvalue()


class TestDaemonSSL(PathocTestDaemon):
    ssl = True
    ssloptions = dict(
        request_client_cert=True,
        sans=[b"test1.com", b"test2.com"],
        alpn_select=b'h2',
    )

    def test_sni(self):
        self.tval(
            ["get:/p/200"],
            sni="foobar.com"
        )
        log = self.d.log()
        assert log[0]["request"]["sni"] == "foobar.com"

    def test_showssl(self):
        assert "certificate chain" in self.tval(["get:/p/200"], showssl=True)

    def test_clientcert(self):
        self.tval(
            ["get:/p/200"],
            clientcert=tutils.test_data.path("pathod/data/clientcert/client.pem"),
        )
        log = self.d.log()
        assert log[0]["request"]["clientcert"]["keyinfo"]

    def test_http2_without_ssl(self):
        fp = io.StringIO()
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            use_http2=True,
            ssl=False,
            fp=fp
        )
        with pytest.raises(NotImplementedError):
            c.connect()


class TestDaemon(PathocTestDaemon):
    ssl = False

    def test_ssl_error(self):
        c = pathoc.Pathoc(("127.0.0.1", self.d.port), ssl=True, fp=None)
        try:
            with c.connect():
                pass
        except Exception as e:
            assert "SSL" in str(e)
        else:
            raise AssertionError("No exception raised.")

    def test_showssl(self):
        assert "certificate chain" not in self.tval(
            ["get:/p/200"],
            showssl=True)

    def test_ignorecodes(self):
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" not in self.tval(["get:'/p/200:b@1'"], ignorecodes=[200])
        assert "200" not in self.tval(
            ["get:'/p/200:b@1'"],
            ignorecodes=[
                200,
                201])
        assert "202" in self.tval(["get:'/p/202:b@1'"], ignorecodes=[200, 201])

    def _test_timeout(self):
        assert "Timeout" in self.tval(["get:'/p/200:p0,100'"], timeout=0.01)
        assert "HTTP" in self.tval(
            ["get:'/p/200:p5,100'"],
            showresp=True,
            timeout=1
        )
        assert "HTTP" not in self.tval(
            ["get:'/p/200:p3,100'"],
            showresp=True,
            timeout=1,
            ignoretimeout=True
        )

    def test_showresp(self):
        reqs = ["get:/p/200:da", "get:/p/200:da"]
        assert self.tval(reqs).count("200 OK") == 2
        assert self.tval(reqs, showresp=True).count("HTTP/1.1 200 OK") == 2
        assert self.tval(
            reqs, showresp=True, hexdump=True
        ).count("0000000000") == 2

    def test_showresp_httperr(self):
        v = self.tval(["get:'/p/200:d20'"], showresp=True, showsummary=True)
        assert "Invalid header" in v
        assert "HTTP/" in v

    def test_explain(self):
        reqs = ["get:/p/200:b@100"]
        assert "b@100" not in self.tval(reqs, explain=True)

    def test_showreq(self):
        reqs = ["get:/p/200:da", "get:/p/200:da"]
        assert self.tval(reqs, showreq=True).count("GET /p/200") == 2
        assert self.tval(
            reqs, showreq=True, hexdump=True
        ).count("0000000000") == 2

    def test_conn_err(self):
        assert "Invalid server response" in self.tval(["get:'/p/200:d2'"])

    def test_websocket_shutdown(self):
        self.tval(["ws:/"])

    def test_wait_finish(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            fp=None,
            ws_read_limit=1
        )
        with c.connect():
            c.request("ws:/")
            c.request("wf:f'wf'")
            # This should read a frame and close the websocket reader
            assert len([i for i in c.wait(timeout=5, finish=False)]) == 1
            assert not [i for i in c.wait(timeout=0)]

    def test_connect_fail(self):
        to = ("foobar", 80)
        c = pathoc.Pathoc(("127.0.0.1", self.d.port), fp=None)
        c.rfile, c.wfile = io.BytesIO(), io.BytesIO()
        with pytest.raises(Exception, match="CONNECT failed"):
            c.http_connect(to)
        c.rfile = io.BytesIO(
            b"HTTP/1.1 500 OK\r\n"
        )
        with pytest.raises(Exception, match="CONNECT failed"):
            c.http_connect(to)
        c.rfile = io.BytesIO(
            b"HTTP/1.1 200 OK\r\n"
        )
        c.http_connect(to)

    def test_socks_connect(self):
        to = ("foobar", 80)
        c = pathoc.Pathoc(("127.0.0.1", self.d.port), fp=None)
        c.rfile, c.wfile = tutils.treader(b""), io.BytesIO()
        with pytest.raises(pathoc.PathocError):
            c.socks_connect(to)

        c.rfile = tutils.treader(
            b"\x05\xEE"
        )
        with pytest.raises(Exception, match="SOCKS without authentication"):
            c.socks_connect(("example.com", 0xDEAD))

        c.rfile = tutils.treader(
            b"\x05\x00" +
            b"\x05\xEE\x00\x03\x0bexample.com\xDE\xAD"
        )
        with pytest.raises(Exception, match="SOCKS server error"):
            c.socks_connect(("example.com", 0xDEAD))

        c.rfile = tutils.treader(
            b"\x05\x00" +
            b"\x05\x00\x00\x03\x0bexample.com\xDE\xAD"
        )
        c.socks_connect(("example.com", 0xDEAD))


class TestDaemonHTTP2(PathocTestDaemon):
    ssl = True
    explain = False

    def test_http2(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            fp=None,
            ssl=True,
            use_http2=True,
        )
        assert isinstance(c.protocol, HTTP2StateProtocol)

        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
        )
        assert c.protocol == http1

    def test_http2_alpn(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            fp=None,
            ssl=True,
            use_http2=True,
            http2_skip_connection_preface=True,
        )

        tmp_convert_to_tls = c.convert_to_tls
        c.convert_to_tls = Mock()
        c.convert_to_tls.side_effect = tmp_convert_to_tls
        with c.connect():
            _, kwargs = c.convert_to_tls.call_args
            assert set(kwargs['alpn_protos']) == set([b'http/1.1', b'h2'])

    def test_request(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            fp=None,
            ssl=True,
            use_http2=True,
        )
        with c.connect():
            resp = c.request("get:/p/200")
        assert resp.status_code == 200
