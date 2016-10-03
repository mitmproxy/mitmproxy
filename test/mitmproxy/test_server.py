import os
import socket
import time
import types

import netlib.tutils
from mitmproxy import controller
from mitmproxy import options
from mitmproxy.builtins import script
from mitmproxy.models import Error, HTTPResponse, HTTPFlow
from mitmproxy.proxy.config import HostMatcher, parse_server_spec
from netlib import tcp, http, socks
from netlib.certutils import SSLCert
from netlib.exceptions import HttpReadDisconnect, HttpException
from netlib.http import authentication, http1
from netlib.tcp import Address
from netlib.tutils import raises
from pathod import pathoc, pathod

from . import tutils, tservers

"""
    Note that the choice of response code in these tests matters more than you
    might think. libcurl treats a 304 response code differently from, say, a
    200 response code - it will correctly terminate a 304 response with no
    content-length header, whereas it will block forever waiting for content
    for a 200 response.
"""


class CommonMixin:

    def test_large(self):
        assert len(self.pathod("200:b@50k").content) == 1024 * 50

    @staticmethod
    def wait_until_not_live(flow):
        """
        Race condition: We don't want to replay the flow while it is still live.
        """
        s = time.time()
        while flow.live:
            time.sleep(0.001)
            if time.time() - s > 5:
                raise RuntimeError("Flow is live for too long.")

    def test_replay(self):
        assert self.pathod("304").status_code == 304
        if isinstance(self, tservers.HTTPUpstreamProxyTest) and self.ssl:
            assert len(self.master.state.view) == 2
        else:
            assert len(self.master.state.view) == 1
        l = self.master.state.view[-1]
        assert l.response.status_code == 304
        l.request.path = "/p/305"
        self.wait_until_not_live(l)
        rt = self.master.replay_request(l, block=True)
        assert l.response.status_code == 305

        # Disconnect error
        l.request.path = "/p/305:d0"
        rt = self.master.replay_request(l, block=True)
        assert rt
        if isinstance(self, tservers.HTTPUpstreamProxyTest):
            assert l.response.status_code == 502
        else:
            assert l.error

        # Port error
        l.request.port = 1
        # In upstream mode, we get a 502 response from the upstream proxy server.
        # In upstream mode with ssl, the replay will fail as we cannot establish
        # SSL with the upstream proxy.
        rt = self.master.replay_request(l, block=True)
        assert rt
        if isinstance(self, tservers.HTTPUpstreamProxyTest):
            assert l.response.status_code == 502
        else:
            assert l.error

    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        # In Upstream mode with SSL, we may already have a previous CONNECT
        # request.
        l = self.master.state.view[-1]
        assert l.client_conn.address
        assert "host" in l.request.headers
        assert l.response.status_code == 304

    def test_invalid_http(self):
        t = tcp.TCPClient(("127.0.0.1", self.proxy.port))
        with t.connect():
            t.wfile.write(b"invalid\r\n\r\n")
            t.wfile.flush()
            line = t.rfile.readline()
            assert (b"Bad Request" in line) or (b"Bad Gateway" in line)

    def test_sni(self):
        if not self.ssl:
            return

        if getattr(self, 'reverse', False):
            # In reverse proxy mode, we expect to use the upstream host as our SNI value
            expected_sni = "127.0.0.1"
        else:
            expected_sni = "testserver.com"

        f = self.pathod("304", sni="testserver.com")
        assert f.status_code == 304
        log = self.server.last_log()
        assert log["request"]["sni"] == expected_sni


class TcpMixin:

    def _ignore_on(self):
        assert not hasattr(self, "_ignore_backup")
        self._ignore_backup = self.config.check_ignore
        self.config.check_ignore = HostMatcher(
            [".+:%s" % self.server.port] + self.config.check_ignore.patterns)

    def _ignore_off(self):
        assert hasattr(self, "_ignore_backup")
        self.config.check_ignore = self._ignore_backup
        del self._ignore_backup

    def test_ignore(self):
        n = self.pathod("304")
        self._ignore_on()
        i = self.pathod("305")
        i2 = self.pathod("306")
        self._ignore_off()

        self.master.event_queue.join()

        assert n.status_code == 304
        assert i.status_code == 305
        assert i2.status_code == 306
        assert any(f.response.status_code == 304 for f in self.master.state.flows)
        assert not any(f.response.status_code == 305 for f in self.master.state.flows)
        assert not any(f.response.status_code == 306 for f in self.master.state.flows)

        # Test that we get the original SSL cert
        if self.ssl:
            i_cert = SSLCert(i.sslinfo.certchain[0])
            i2_cert = SSLCert(i2.sslinfo.certchain[0])
            n_cert = SSLCert(n.sslinfo.certchain[0])

            assert i_cert == i2_cert
            assert i_cert != n_cert

        # Test Non-HTTP traffic
        spec = "200:i0,@100:d0"  # this results in just 100 random bytes
        # mitmproxy responds with bad gateway
        assert self.pathod(spec).status_code == 502
        self._ignore_on()
        with raises(HttpException):
            self.pathod(spec)  # pathoc tries to parse answer as HTTP

        self._ignore_off()

    def _tcpproxy_on(self):
        assert not hasattr(self, "_tcpproxy_backup")
        self._tcpproxy_backup = self.config.check_tcp
        self.config.check_tcp = HostMatcher(
            [".+:%s" % self.server.port] + self.config.check_tcp.patterns)

    def _tcpproxy_off(self):
        assert hasattr(self, "_tcpproxy_backup")
        self.config.check_tcp = self._tcpproxy_backup
        del self._tcpproxy_backup

    def test_tcp(self):
        n = self.pathod("304")
        self._tcpproxy_on()
        i = self.pathod("305")
        i2 = self.pathod("306")
        self._tcpproxy_off()

        self.master.event_queue.join()

        assert n.status_code == 304
        assert i.status_code == 305
        assert i2.status_code == 306
        assert any(f.response.status_code == 304 for f in self.master.state.flows if isinstance(f, HTTPFlow))
        assert not any(f.response.status_code == 305 for f in self.master.state.flows if isinstance(f, HTTPFlow))
        assert not any(f.response.status_code == 306 for f in self.master.state.flows if isinstance(f, HTTPFlow))

        # Test that we get the original SSL cert
        if self.ssl:
            i_cert = SSLCert(i.sslinfo.certchain[0])
            i2_cert = SSLCert(i2.sslinfo.certchain[0])
            n_cert = SSLCert(n.sslinfo.certchain[0])

            assert i_cert == i2_cert == n_cert

        # Make sure that TCP messages are in the event log.
        # Re-enable and fix this when we start keeping TCPFlows in the state.
        # assert any("305" in m for m in self.master.tlog)
        # assert any("306" in m for m in self.master.tlog)


class AppMixin:

    def test_app(self):
        ret = self.app("/")
        assert ret.status_code == 200
        assert b"mitmproxy" in ret.content


class TestHTTP(tservers.HTTPProxyTest, CommonMixin, AppMixin):

    def test_app_err(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://errapp/'")
        assert ret.status_code == 500
        assert b"ValueError" in ret.content

    def test_invalid_connect(self):
        t = tcp.TCPClient(("127.0.0.1", self.proxy.port))
        with t.connect():
            t.wfile.write(b"CONNECT invalid\n\n")
            t.wfile.flush()
            assert b"Bad Request" in t.rfile.readline()

    def test_upstream_ssl_error(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'https://localhost:%s/'" % self.server.port)
        assert ret.status_code == 400

    def test_connection_close(self):
        # Add a body, so we have a content-length header, which combined with
        # HTTP1.1 means the connection is kept alive.
        response = '%s/p/200:b@1' % self.server.urlbase

        # Lets sanity check that the connection does indeed stay open by
        # issuing two requests over the same connection
        p = self.pathoc()
        with p.connect():
            assert p.request("get:'%s'" % response)
            assert p.request("get:'%s'" % response)

        # Now check that the connection is closed as the client specifies
        p = self.pathoc()
        with p.connect():
            assert p.request("get:'%s':h'Connection'='close'" % response)
            # There's a race here, which means we can get any of a number of errors.
            # Rather than introduce yet another sleep into the test suite, we just
            # relax the Exception specification.
            with raises(Exception):
                p.request("get:'%s'" % response)

    def test_reconnect(self):
        req = "get:'%s/p/200:b@1:da'" % self.server.urlbase
        p = self.pathoc()
        with p.connect():
            assert p.request(req)
            # Server has disconnected. Mitmproxy should detect this, and reconnect.
            assert p.request(req)
            assert p.request(req)

    def test_get_connection_switching(self):
        def switched(l):
            for i in l:
                if "serverdisconnect" in i:
                    return True

        req = "get:'%s/p/200:b@1'"
        p = self.pathoc()
        with p.connect():
            assert p.request(req % self.server.urlbase)
            assert p.request(req % self.server2.urlbase)
        assert switched(self.proxy.tlog)

    def test_blank_leading_line(self):
        p = self.pathoc()
        with p.connect():
            req = "get:'%s/p/201':i0,'\r\n'"
            assert p.request(req % self.server.urlbase).status_code == 201

    def test_invalid_headers(self):
        p = self.pathoc()
        with p.connect():
            resp = p.request("get:'http://foo':h':foo'='bar'")
        assert resp.status_code == 400

    def test_stream(self):
        self.master.set_stream_large_bodies(1024 * 2)

        self.pathod("200:b@1k")
        assert not self.master.state.view[-1].response.stream
        assert len(self.master.state.view[-1].response.content) == 1024 * 1

        self.pathod("200:b@3k")
        assert self.master.state.view[-1].response.stream
        assert self.master.state.view[-1].response.content is None
        self.master.set_stream_large_bodies(None)

    def test_stream_modify(self):
        s = script.Script(
            tutils.test_data.path("data/addonscripts/stream_modify.py")
        )
        self.master.addons.add(s)
        d = self.pathod('200:b"foo"')
        assert d.content == b"bar"
        self.master.addons.remove(s)


class TestHTTPAuth(tservers.HTTPProxyTest):
    def test_auth(self):
        self.master.options.auth_singleuser = "test:test"
        assert self.pathod("202").status_code == 407
        p = self.pathoc()
        with p.connect():
            ret = p.request("""
                get
                'http://localhost:%s/p/202'
                h'%s'='%s'
            """ % (
                self.server.port,
                http.authentication.BasicProxyAuth.AUTH_HEADER,
                authentication.assemble_http_basic_auth("basic", "test", "test")
            ))
        assert ret.status_code == 202


class TestHTTPReverseAuth(tservers.ReverseProxyTest):
    def test_auth(self):
        self.master.options.auth_singleuser = "test:test"
        assert self.pathod("202").status_code == 401
        p = self.pathoc()
        with p.connect():
            ret = p.request("""
                get
                '/p/202'
                h'%s'='%s'
            """ % (
                http.authentication.BasicWebsiteAuth.AUTH_HEADER,
                authentication.assemble_http_basic_auth("basic", "test", "test")
            ))
        assert ret.status_code == 202


class TestHTTPS(tservers.HTTPProxyTest, CommonMixin, TcpMixin):
    ssl = True
    ssloptions = pathod.SSLOptions(request_client_cert=True)

    def test_clientcert_file(self):
        try:
            self.config.clientcerts = os.path.join(
                tutils.test_data.path("data/clientcert"), "client.pem")
            f = self.pathod("304")
            assert f.status_code == 304
            assert self.server.last_log()["request"]["clientcert"]["keyinfo"]
        finally:
            self.config.clientcerts = None

    def test_clientcert_dir(self):
        try:
            self.config.clientcerts = tutils.test_data.path("data/clientcert")
            f = self.pathod("304")
            assert f.status_code == 304
            assert self.server.last_log()["request"]["clientcert"]["keyinfo"]
        finally:
            self.config.clientcerts = None

    def test_error_post_connect(self):
        p = self.pathoc()
        with p.connect():
            assert p.request("get:/:i0,'invalid\r\n\r\n'").status_code == 400


class TestHTTPSCertfile(tservers.HTTPProxyTest, CommonMixin):
    ssl = True
    certfile = True

    def test_certfile(self):
        assert self.pathod("304")


class TestHTTPSSecureByDefault:
    def test_secure_by_default(self):
        """
        Certificate verification should be turned on by default.
        """
        default_opts = options.Options()
        assert not default_opts.ssl_insecure


class TestHTTPSUpstreamServerVerificationWTrustedCert(tservers.HTTPProxyTest):

    """
    Test upstream server certificate verification with a trusted server cert.
    """
    ssl = True
    ssloptions = pathod.SSLOptions(
        cn=b"example.mitmproxy.org",
        certs=[
            ("example.mitmproxy.org", tutils.test_data.path("data/servercert/trusted-leaf.pem"))
        ]
    )

    def _request(self):
        p = self.pathoc(sni="example.mitmproxy.org")
        with p.connect():
            return p.request("get:/p/242")

    def test_verification_w_cadir(self):
        self.config.options.update(
            ssl_insecure=False,
            ssl_verify_upstream_trusted_cadir=tutils.test_data.path(
                "data/servercert/"
            ),
            ssl_verify_upstream_trusted_ca=None,
        )
        assert self._request().status_code == 242

    def test_verification_w_pemfile(self):
        self.config.options.update(
            ssl_insecure=False,
            ssl_verify_upstream_trusted_cadir=None,
            ssl_verify_upstream_trusted_ca=tutils.test_data.path(
                "data/servercert/trusted-root.pem"
            ),
        )
        assert self._request().status_code == 242


class TestHTTPSUpstreamServerVerificationWBadCert(tservers.HTTPProxyTest):

    """
    Test upstream server certificate verification with an untrusted server cert.
    """
    ssl = True
    ssloptions = pathod.SSLOptions(
        cn=b"example.mitmproxy.org",
        certs=[
            ("example.mitmproxy.org", tutils.test_data.path("data/servercert/self-signed.pem"))
        ])

    def _request(self):
        p = self.pathoc(sni="example.mitmproxy.org")
        with p.connect():
            return p.request("get:/p/242")

    @classmethod
    def get_options(cls):
        opts = super(tservers.HTTPProxyTest, cls).get_options()
        opts.ssl_verify_upstream_trusted_ca = tutils.test_data.path(
            "data/servercert/trusted-root.pem"
        )
        return opts

    def test_no_verification_w_bad_cert(self):
        self.config.options.ssl_insecure = True
        r = self._request()
        assert r.status_code == 242

    def test_verification_w_bad_cert(self):
        # We only test for a single invalid cert here.
        # Actual testing of different root-causes (invalid hostname, expired, ...)
        # is done in netlib.
        self.config.options.ssl_insecure = False
        r = self._request()
        assert r.status_code == 502
        assert b"Certificate Verification Error" in r.raw_content


class TestHTTPSNoCommonName(tservers.HTTPProxyTest):

    """
    Test what happens if we get a cert without common name back.
    """
    ssl = True
    ssloptions = pathod.SSLOptions(
        certs=[
            (b"*", tutils.test_data.path("data/no_common_name.pem"))
        ]
    )

    def test_http(self):
        f = self.pathod("202")
        assert f.sslinfo.certchain[0].get_subject().CN == "127.0.0.1"


class TestReverse(tservers.ReverseProxyTest, CommonMixin, TcpMixin):
    reverse = True


class TestReverseSSL(tservers.ReverseProxyTest, CommonMixin, TcpMixin):
    reverse = True
    ssl = True


class TestSocks5(tservers.SocksModeTest):

    def test_simple(self):
        p = self.pathoc()
        with p.connect():
            p.socks_connect(("localhost", self.server.port))
            f = p.request("get:/p/200")
        assert f.status_code == 200

    def test_with_authentication_only(self):
        p = self.pathoc()
        with p.connect():
            f = p.request("get:/p/200")
        assert f.status_code == 502
        assert b"SOCKS5 mode failure" in f.content

    def test_no_connect(self):
        """
        mitmproxy doesn't support UDP or BIND SOCKS CMDs
        """
        p = self.pathoc()
        with p.connect():
            socks.ClientGreeting(
                socks.VERSION.SOCKS5,
                [socks.METHOD.NO_AUTHENTICATION_REQUIRED]
            ).to_file(p.wfile)
            socks.Message(
                socks.VERSION.SOCKS5,
                socks.CMD.BIND,
                socks.ATYP.DOMAINNAME,
                ("example.com", 8080)
            ).to_file(p.wfile)

            p.wfile.flush()
            p.rfile.read(2)  # read server greeting
            f = p.request("get:/p/200")  # the request doesn't matter, error response from handshake will be read anyway.
        assert f.status_code == 502
        assert b"SOCKS5 mode failure" in f.content


class TestHttps2Http(tservers.ReverseProxyTest):

    @classmethod
    def get_options(cls):
        opts = super(TestHttps2Http, cls).get_options()
        s = parse_server_spec(opts.upstream_server)
        opts.upstream_server = "http://%s" % s.address
        return opts

    def pathoc(self, ssl, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = pathoc.Pathoc(
            ("localhost", self.proxy.port), ssl=True, sni=sni, fp=None
        )
        return p

    def test_all(self):
        p = self.pathoc(ssl=True)
        with p.connect():
            assert p.request("get:'/p/200'").status_code == 200

    def test_sni(self):
        p = self.pathoc(ssl=True, sni="example.com")
        with p.connect():
            assert p.request("get:'/p/200'").status_code == 200
            assert all("Error in handle_sni" not in msg for msg in self.proxy.tlog)

    def test_http(self):
        p = self.pathoc(ssl=False)
        with p.connect():
            assert p.request("get:'/p/200'").status_code == 200


class TestTransparent(tservers.TransparentProxyTest, CommonMixin, TcpMixin):
    ssl = False

    def test_tcp_stream_modify(self):
        s = script.Script(
            tutils.test_data.path("data/addonscripts/tcp_stream_modify.py")
        )
        self.master.addons.add(s)
        self._tcpproxy_on()
        d = self.pathod('200:b"foo"')
        self._tcpproxy_off()
        assert d.content == b"bar"
        self.master.addons.remove(s)


class TestTransparentSSL(tservers.TransparentProxyTest, CommonMixin, TcpMixin):
    ssl = True

    def test_sslerr(self):
        p = pathoc.Pathoc(("localhost", self.proxy.port), fp=None)
        p.connect()
        r = p.request("get:/")
        assert r.status_code == 502


class TestProxy(tservers.HTTPProxyTest):

    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        f = self.master.state.view[0]
        assert f.client_conn.address
        assert "host" in f.request.headers
        assert f.response.status_code == 304

    @tutils.skip_appveyor
    def test_response_timestamps(self):
        # test that we notice at least 1 sec delay between timestamps
        # in response object
        f = self.pathod("304:b@1k:p50,1")
        assert f.status_code == 304

        response = self.master.state.view[0].response
        # timestamp_start might fire a bit late, so we play safe and only require 300ms.
        assert 0.3 <= response.timestamp_end - response.timestamp_start

    @tutils.skip_appveyor
    def test_request_timestamps(self):
        # test that we notice a delay between timestamps in request object
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))

        # call pathod server, wait a second to complete the request
        connection.send(
            b"GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n" %
            self.server.port)
        time.sleep(1)
        connection.send(b"\r\n")
        connection.recv(50000)
        connection.close()

        request, response = self.master.state.view[
            0].request, self.master.state.view[0].response
        assert response.status_code == 304  # sanity test for our low level request
        # timestamp_start might fire a bit late, so we play safe and only require 300ms.
        assert 0.3 <= request.timestamp_end - request.timestamp_start

    def test_request_tcp_setup_timestamp_presence(self):
        # tests that the client_conn a tcp connection has a tcp_setup_timestamp
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("localhost", self.proxy.port))
        connection.send(
            b"GET http://localhost:%d/p/200:b@1k HTTP/1.1\r\n" %
            self.server.port)
        connection.send(b"\r\n")
        # a bit hacky: make sure that we don't just read the headers only.
        recvd = 0
        while recvd < 1024:
            recvd += len(connection.recv(5000))
        connection.send(
            b"GET http://localhost:%d/p/200:b@1k HTTP/1.1\r\n" %
            self.server.port)
        connection.send(b"\r\nb")
        recvd = 0
        while recvd < 1024:
            recvd += len(connection.recv(5000))
        connection.close()

        first_flow = self.master.state.view[0]
        second_flow = self.master.state.view[1]
        assert first_flow.server_conn.timestamp_tcp_setup
        assert first_flow.server_conn.timestamp_ssl_setup is None
        assert second_flow.server_conn.timestamp_tcp_setup
        assert first_flow.server_conn.timestamp_tcp_setup == second_flow.server_conn.timestamp_tcp_setup

    def test_request_ip(self):
        f = self.pathod("200:b@100")
        assert f.status_code == 200
        f = self.master.state.view[0]
        assert f.server_conn.address == ("127.0.0.1", self.server.port)


class TestProxySSL(tservers.HTTPProxyTest):
    ssl = True

    def test_request_ssl_setup_timestamp_presence(self):
        # tests that the ssl timestamp is present when ssl is used
        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        first_flow = self.master.state.view[0]
        assert first_flow.server_conn.timestamp_ssl_setup


class MasterRedirectRequest(tservers.TestMaster):
    redirect_port = None  # Set by TestRedirectRequest

    @controller.handler
    def request(self, f):
        if f.request.path == "/p/201":

            # This part should have no impact, but it should also not cause any exceptions.
            addr = f.live.server_conn.address
            addr2 = Address(("127.0.0.1", self.redirect_port))
            f.live.set_server(addr2)
            f.live.set_server(addr)

            # This is the actual redirection.
            f.request.port = self.redirect_port
        super(MasterRedirectRequest, self).request(f)

    @controller.handler
    def response(self, f):
        f.response.content = bytes(f.client_conn.address.port)
        f.response.headers["server-conn-id"] = str(f.server_conn.source_address.port)
        super(MasterRedirectRequest, self).response(f)


class TestRedirectRequest(tservers.HTTPProxyTest):
    masterclass = MasterRedirectRequest
    ssl = True

    def test_redirect(self):
        """
        Imagine a single HTTPS connection with three requests:

        1. First request should pass through unmodified
        2. Second request will be redirected to a different host by an inline script
        3. Third request should pass through unmodified

        This test verifies that the original destination is restored for the third request.
        """
        self.master.redirect_port = self.server2.port

        p = self.pathoc()
        with p.connect():
            self.server.clear_log()
            self.server2.clear_log()
            r1 = p.request("get:'/p/200'")
            assert r1.status_code == 200
            assert self.server.last_log()
            assert not self.server2.last_log()

            self.server.clear_log()
            self.server2.clear_log()
            r2 = p.request("get:'/p/201'")
            assert r2.status_code == 201
            assert not self.server.last_log()
            assert self.server2.last_log()

            self.server.clear_log()
            self.server2.clear_log()
            r3 = p.request("get:'/p/202'")
            assert r3.status_code == 202
            assert self.server.last_log()
            assert not self.server2.last_log()

            assert r1.content == r2.content == r3.content


class MasterStreamRequest(tservers.TestMaster):

    """
        Enables the stream flag on the flow for all requests
    """
    @controller.handler
    def responseheaders(self, f):
        f.response.stream = True


class TestStreamRequest(tservers.HTTPProxyTest):
    masterclass = MasterStreamRequest

    def test_stream_simple(self):
        p = self.pathoc()
        with p.connect():
            # a request with 100k of data but without content-length
            r1 = p.request("get:'%s/p/200:r:b@100k:d102400'" % self.server.urlbase)
            assert r1.status_code == 200
            assert len(r1.content) > 100000

    def test_stream_multiple(self):
        p = self.pathoc()
        with p.connect():
            # simple request with streaming turned on
            r1 = p.request("get:'%s/p/200'" % self.server.urlbase)
            assert r1.status_code == 200

            # now send back 100k of data, streamed but not chunked
            r1 = p.request("get:'%s/p/201:b@100k'" % self.server.urlbase)
            assert r1.status_code == 201

    def test_stream_chunked(self):
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))
        fconn = connection.makefile("rb")
        spec = '200:h"Transfer-Encoding"="chunked":r:b"4\\r\\nthis\\r\\n11\\r\\nisatest__reachhex\\r\\n0\\r\\n\\r\\n"'
        connection.send(
            b"GET %s/p/%s HTTP/1.1\r\n" %
            (self.server.urlbase.encode(), spec.encode()))
        connection.send(b"\r\n")

        resp = http1.read_response_head(fconn)

        assert resp.headers["Transfer-Encoding"] == 'chunked'
        assert resp.status_code == 200

        chunks = list(http1.read_body(fconn, None))
        assert chunks == [b"this", b"isatest__reachhex"]

        connection.close()


class MasterFakeResponse(tservers.TestMaster):
    @controller.handler
    def request(self, f):
        f.response = HTTPResponse.wrap(netlib.tutils.tresp())


class TestFakeResponse(tservers.HTTPProxyTest):
    masterclass = MasterFakeResponse

    def test_fake(self):
        f = self.pathod("200")
        assert "header-response" in f.headers


class TestServerConnect(tservers.HTTPProxyTest):
    masterclass = MasterFakeResponse
    ssl = True

    @classmethod
    def get_options(cls):
        opts = tservers.HTTPProxyTest.get_options()
        opts.no_upstream_cert = True
        return opts

    def test_unnecessary_serverconnect(self):
        """A replayed/fake response with no_upstream_cert should not connect to an upstream server"""
        assert self.pathod("200").status_code == 200
        for msg in self.proxy.tmaster.tlog:
            assert "serverconnect" not in msg


class MasterKillRequest(tservers.TestMaster):

    @controller.handler
    def request(self, f):
        f.reply.kill()


class TestKillRequest(tservers.HTTPProxyTest):
    masterclass = MasterKillRequest

    def test_kill(self):
        with raises(HttpReadDisconnect):
            self.pathod("200")
        # Nothing should have hit the server
        assert not self.server.last_log()


class MasterKillResponse(tservers.TestMaster):

    @controller.handler
    def response(self, f):
        f.reply.kill()


class TestKillResponse(tservers.HTTPProxyTest):
    masterclass = MasterKillResponse

    def test_kill(self):
        with raises(HttpReadDisconnect):
            self.pathod("200")
        # The server should have seen a request
        assert self.server.last_log()


class EResolver(tservers.TResolver):

    def original_addr(self, sock):
        raise RuntimeError("Could not resolve original destination.")


class TestTransparentResolveError(tservers.TransparentProxyTest):
    resolver = EResolver

    def test_resolve_error(self):
        assert self.pathod("304").status_code == 502


class MasterIncomplete(tservers.TestMaster):

    @controller.handler
    def request(self, f):
        resp = HTTPResponse.wrap(netlib.tutils.tresp())
        resp.content = None
        f.response = resp


class TestIncompleteResponse(tservers.HTTPProxyTest):
    masterclass = MasterIncomplete

    def test_incomplete(self):
        assert self.pathod("200").status_code == 502


class TestUpstreamProxy(tservers.HTTPUpstreamProxyTest, CommonMixin, AppMixin):
    ssl = False

    def test_order(self):
        self.proxy.tmaster.options.replacements = [
            ("~q", "foo", "bar"),
            ("~q", "bar", "baz"),
            ("~q", "foo", "oh noes!"),
            ("~s", "baz", "ORLY")
        ]
        p = self.pathoc()
        with p.connect():
            req = p.request("get:'%s/p/418:b\"foo\"'" % self.server.urlbase)
        assert req.content == b"ORLY"
        assert req.status_code == 418


class TestUpstreamProxySSL(
        tservers.HTTPUpstreamProxyTest,
        CommonMixin,
        TcpMixin):
    ssl = True

    def _host_pattern_on(self, attr):
        """
        Updates config.check_tcp or check_ignore, depending on attr.
        """
        assert not hasattr(self, "_ignore_%s_backup" % attr)
        backup = []
        for proxy in self.chain:
            old_matcher = getattr(
                proxy.tmaster.server.config,
                "check_%s" %
                attr)
            backup.append(old_matcher)
            setattr(
                proxy.tmaster.server.config,
                "check_%s" % attr,
                HostMatcher([".+:%s" % self.server.port] + old_matcher.patterns)
            )

        setattr(self, "_ignore_%s_backup" % attr, backup)

    def _host_pattern_off(self, attr):
        backup = getattr(self, "_ignore_%s_backup" % attr)
        for proxy in reversed(self.chain):
            setattr(
                proxy.tmaster.server.config,
                "check_%s" % attr,
                backup.pop()
            )

        assert not backup
        delattr(self, "_ignore_%s_backup" % attr)

    def _ignore_on(self):
        super(TestUpstreamProxySSL, self)._ignore_on()
        self._host_pattern_on("ignore")

    def _ignore_off(self):
        super(TestUpstreamProxySSL, self)._ignore_off()
        self._host_pattern_off("ignore")

    def _tcpproxy_on(self):
        super(TestUpstreamProxySSL, self)._tcpproxy_on()
        self._host_pattern_on("tcp")

    def _tcpproxy_off(self):
        super(TestUpstreamProxySSL, self)._tcpproxy_off()
        self._host_pattern_off("tcp")

    def test_simple(self):
        p = self.pathoc()
        with p.connect():
            req = p.request("get:'/p/418:b\"content\"'")
        assert req.content == b"content"
        assert req.status_code == 418

        # CONNECT from pathoc to chain[0],
        assert self.proxy.tmaster.state.flow_count() == 2
        # request from pathoc to chain[0]
        # CONNECT from proxy to chain[1],
        assert self.chain[0].tmaster.state.flow_count() == 2
        # request from proxy to chain[1]
        # request from chain[0] (regular proxy doesn't store CONNECTs)
        assert self.chain[1].tmaster.state.flow_count() == 1


class TestProxyChainingSSLReconnect(tservers.HTTPUpstreamProxyTest):
    ssl = True

    def test_reconnect(self):
        """
        Tests proper functionality of ConnectionHandler.server_reconnect mock.
        If we have a disconnect on a secure connection that's transparently proxified to
        an upstream http proxy, we need to send the CONNECT request again.
        """

        def kill_requests(master, attr, exclude):
            k = [0]  # variable scope workaround: put into array
            _func = getattr(master, attr)

            @controller.handler
            def handler(*args):
                f = args[-1]
                k[0] += 1
                if not (k[0] in exclude):
                    f.client_conn.finish()
                    f.error = Error("terminated")
                    f.reply.kill()
                return _func(f)

            setattr(master, attr, types.MethodType(handler, master))

        kill_requests(
            self.chain[1].tmaster,
            "request",
            exclude = [
                # fail first request
                2,  # allow second request
            ]
        )

        kill_requests(self.chain[0].tmaster, "request",
                      exclude=[
                          1,  # CONNECT
                          # fail first request
                          3,  # reCONNECT
                          4,  # request
        ])

        p = self.pathoc()
        with p.connect():
            req = p.request("get:'/p/418:b\"content\"'")
            assert req.content == b"content"
            assert req.status_code == 418

            assert self.proxy.tmaster.state.flow_count() == 2  # CONNECT and request
            # CONNECT, failing request,
            assert self.chain[0].tmaster.state.flow_count() == 4
            # reCONNECT, request
            # failing request, request
            assert self.chain[1].tmaster.state.flow_count() == 2
            # (doesn't store (repeated) CONNECTs from chain[0]
            #  as it is a regular proxy)

            assert not self.chain[1].tmaster.state.flows[0].response  # killed
            assert self.chain[1].tmaster.state.flows[1].response

            assert self.proxy.tmaster.state.flows[0].request.first_line_format == "authority"
            assert self.proxy.tmaster.state.flows[1].request.first_line_format == "relative"

            assert self.chain[0].tmaster.state.flows[
                0].request.first_line_format == "authority"
            assert self.chain[0].tmaster.state.flows[
                1].request.first_line_format == "relative"
            assert self.chain[0].tmaster.state.flows[
                2].request.first_line_format == "authority"
            assert self.chain[0].tmaster.state.flows[
                3].request.first_line_format == "relative"

            assert self.chain[1].tmaster.state.flows[
                0].request.first_line_format == "relative"
            assert self.chain[1].tmaster.state.flows[
                1].request.first_line_format == "relative"

            req = p.request("get:'/p/418:b\"content2\"'")

            assert req.status_code == 502
            assert self.proxy.tmaster.state.flow_count() == 3  # + new request
            # + new request, repeated CONNECT from chain[1]
            assert self.chain[0].tmaster.state.flow_count() == 6
            # (both terminated)
            # nothing happened here
            assert self.chain[1].tmaster.state.flow_count() == 2


class AddUpstreamCertsToClientChainMixin:

    ssl = True
    servercert = tutils.test_data.path("data/servercert/trusted-root.pem")
    ssloptions = pathod.SSLOptions(
        cn=b"example.mitmproxy.org",
        certs=[
            (b"example.mitmproxy.org", servercert)
        ]
    )

    def test_add_upstream_certs_to_client_chain(self):
        with open(self.servercert, "rb") as f:
            d = f.read()
        upstreamCert = SSLCert.from_pem(d)
        p = self.pathoc()
        with p.connect():
            upstream_cert_found_in_client_chain = False
            for receivedCert in p.server_certs:
                if receivedCert.digest('sha256') == upstreamCert.digest('sha256'):
                    upstream_cert_found_in_client_chain = True
                    break
            assert(upstream_cert_found_in_client_chain == self.master.options.add_upstream_certs_to_client_chain)


class TestHTTPSAddUpstreamCertsToClientChainTrue(
    AddUpstreamCertsToClientChainMixin,
    tservers.HTTPProxyTest
):
    """
    If --add-server-certs-to-client-chain is True, then the client should
    receive the upstream server's certificates
    """
    @classmethod
    def get_options(cls):
        opts = super(tservers.HTTPProxyTest, cls).get_options()
        opts.add_upstream_certs_to_client_chain = True
        return opts


class TestHTTPSAddUpstreamCertsToClientChainFalse(
    AddUpstreamCertsToClientChainMixin,
    tservers.HTTPProxyTest
):
    """
    If --add-server-certs-to-client-chain is False, then the client should not
    receive the upstream server's certificates
    """
    @classmethod
    def get_options(cls):
        opts = super(tservers.HTTPProxyTest, cls).get_options()
        opts.add_upstream_certs_to_client_chain = False
        return opts
