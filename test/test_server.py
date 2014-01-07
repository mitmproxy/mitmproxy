import socket, time
import mock
from netlib import tcp, http_auth, http
from libpathod import pathoc, pathod
import tutils, tservers
from libmproxy import flow, proxy

"""
    Note that the choice of response code in these tests matters more than you
    might think. libcurl treats a 304 response code differently from, say, a
    200 response code - it will correctly terminate a 304 response with no
    content-length header, whereas it will block forever waiting for content
    for a 200 response.
"""

class CommonMixin:
    def test_large(self):
        assert len(self.pathod("200:b@50k").content) == 1024*50

    def test_replay(self):
        assert self.pathod("304").status_code == 304
        assert len(self.master.state.view) == 1
        l = self.master.state.view[0]
        assert l.response.code == 304
        l.request.path = "/p/305"
        rt = self.master.replay_request(l, block=True)
        assert l.response.code == 305

        # Disconnect error
        l.request.path = "/p/305:d0"
        rt = self.master.replay_request(l, block=True)
        assert l.error

        # Port error
        l.request.port = 1
        self.master.replay_request(l, block=True)
        assert l.error

    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.master.state.view[0]
        assert l.request.client_conn.address
        assert "host" in l.request.headers
        assert l.response.code == 304

    def test_invalid_http(self):
        t = tcp.TCPClient("127.0.0.1", self.proxy.port)
        t.connect()
        t.wfile.write("invalid\r\n\r\n")
        t.wfile.flush()
        assert "Bad Request" in t.rfile.readline()



class AppMixin:
    def test_app(self):
        ret = self.app("/")
        assert ret.status_code == 200
        assert "mitmproxy" in ret.content



class TestHTTP(tservers.HTTPProxTest, CommonMixin, AppMixin):
    def test_app_err(self):
        p = self.pathoc()
        ret = p.request("get:'http://errapp/'")
        assert ret.status_code == 500
        assert "ValueError" in ret.content

    def test_invalid_connect(self):
        t = tcp.TCPClient("127.0.0.1", self.proxy.port)
        t.connect()
        t.wfile.write("CONNECT invalid\n\n")
        t.wfile.flush()
        assert "Bad Request" in t.rfile.readline()

    def test_upstream_ssl_error(self):
        p = self.pathoc()
        ret = p.request("get:'https://localhost:%s/'"%self.server.port)
        assert ret.status_code == 400

    def test_connection_close(self):
        # Add a body, so we have a content-length header, which combined with
        # HTTP1.1 means the connection is kept alive.
        response = '%s/p/200:b@1'%self.server.urlbase

        # Lets sanity check that the connection does indeed stay open by
        # issuing two requests over the same connection
        p = self.pathoc()
        assert p.request("get:'%s'"%response)
        assert p.request("get:'%s'"%response)

        # Now check that the connection is closed as the client specifies
        p = self.pathoc()
        assert p.request("get:'%s':h'Connection'='close'"%response)
        tutils.raises("disconnect", p.request, "get:'%s'"%response)

    def test_reconnect(self):
        req = "get:'%s/p/200:b@1:da'"%self.server.urlbase
        p = self.pathoc()
        assert p.request(req)
        # Server has disconnected. Mitmproxy should detect this, and reconnect.
        assert p.request(req)
        assert p.request(req)

        # However, if the server disconnects on our first try, it's an error.
        req = "get:'%s/p/200:b@1:d0'"%self.server.urlbase
        p = self.pathoc()
        tutils.raises("server disconnect", p.request, req)

    def test_proxy_ioerror(self):
        # Tests a difficult-to-trigger condition, where an IOError is raised
        # within our read loop.
        with mock.patch("libmproxy.proxy.ProxyHandler.read_request") as m:
            m.side_effect = IOError("error!")
            tutils.raises("server disconnect", self.pathod, "304")

    def test_get_connection_switching(self):
        def switched(l):
            for i in l:
                if "switching" in i:
                    return True
        req = "get:'%s/p/200:b@1'"
        p = self.pathoc()
        assert p.request(req%self.server.urlbase)
        assert p.request(req%self.server2.urlbase)
        assert switched(self.proxy.log)

    def test_get_connection_err(self):
        p = self.pathoc()
        ret = p.request("get:'http://localhost:0'")
        assert ret.status_code == 502

    def test_blank_leading_line(self):
        p = self.pathoc()
        req = "get:'%s/p/201':i0,'\r\n'"
        assert p.request(req%self.server.urlbase).status_code == 201

    def test_invalid_headers(self):
        p = self.pathoc()
        req = p.request("get:'http://foo':h':foo'='bar'")
        assert req.status_code == 400

    def test_empty_chunked_content(self):
        """
        https://github.com/mitmproxy/mitmproxy/issues/186
        """
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))
        spec = '301:h"Transfer-Encoding"="chunked":r:b"0\\r\\n\\r\\n"'
        connection.send("GET http://localhost:%d/p/%s HTTP/1.1\r\n"%(self.server.port, spec))
        connection.send("\r\n");
        resp = connection.recv(50000)
        connection.close()
        assert "content-length" in resp.lower()

class TestHTTPAuth(tservers.HTTPProxTest):
    authenticator = http_auth.BasicProxyAuth(http_auth.PassManSingleUser("test", "test"), "realm")
    def test_auth(self):
        assert self.pathod("202").status_code == 407
        p = self.pathoc()
        ret = p.request("""
            get
            'http://localhost:%s/p/202'
            h'%s'='%s'
        """%(
            self.server.port,
            http_auth.BasicProxyAuth.AUTH_HEADER,
            http.assemble_http_basic_auth("basic", "test", "test")
        ))
        assert ret.status_code == 202


class TestHTTPConnectSSLError(tservers.HTTPProxTest):
    certfile = True
    def test_go(self):
        p = self.pathoc_raw()
        dst = ("localhost", self.proxy.port)
        p.connect(connect_to=dst)
        tutils.raises("400 - Bad Request", p.http_connect, dst)


class TestHTTPS(tservers.HTTPProxTest, CommonMixin):
    ssl = True
    ssloptions = pathod.SSLOptions(request_client_cert=True)
    clientcerts = True
    def test_clientcert(self):
        f = self.pathod("304")
        assert f.status_code == 304
        assert self.server.last_log()["request"]["clientcert"]["keyinfo"]

    def test_sni(self):
        f = self.pathod("304", sni="testserver.com")
        assert f.status_code == 304
        l = self.server.last_log()
        assert self.server.last_log()["request"]["sni"] == "testserver.com"

    def test_error_post_connect(self):
        p = self.pathoc()
        assert p.request("get:/:i0,'invalid\r\n\r\n'").status_code == 400


class TestHTTPSCertfile(tservers.HTTPProxTest, CommonMixin):
    ssl = True
    certfile = True
    def test_certfile(self):
        assert self.pathod("304")

class TestHTTPSNoCommonName(tservers.HTTPProxTest, CommonMixin):
    """
    Test what happens if we get a cert without common name back.
    """
    ssl = True
    ssloptions=pathod.SSLOptions(certfile=tutils.test_data.path("data/no_common_name.pem"),
                                 keyfile=tutils.test_data.path("data/no_common_name.pem"))

class TestReverse(tservers.ReverseProxTest, CommonMixin):
    reverse = True


class TestTransparent(tservers.TransparentProxTest, CommonMixin):
    ssl = False


class TestTransparentSSL(tservers.TransparentProxTest, CommonMixin):
    ssl = True
    def test_sni(self):
        f = self.pathod("304", sni="testserver.com")
        assert f.status_code == 304
        l = self.server.last_log()
        assert self.server.last_log()["request"]["sni"] == "testserver.com"

    def test_sslerr(self):
        p = pathoc.Pathoc("localhost", self.proxy.port)
        p.connect()
        assert p.request("get:/").status_code == 400


class TestProxy(tservers.HTTPProxTest):
    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.master.state.view[0]
        assert l.request.client_conn.address
        assert "host" in l.request.headers
        assert l.response.code == 304

    def test_response_timestamps(self):
        # test that we notice at least 2 sec delay between timestamps
        # in response object
        f = self.pathod("304:b@1k:p50,1")
        assert f.status_code == 304

        response = self.master.state.view[0].response
        assert 1 <= response.timestamp_end - response.timestamp_start <= 1.2

    def test_request_timestamps(self):
        # test that we notice a delay between timestamps in request object
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))

        # call pathod server, wait a second to complete the request
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        time.sleep(1)
        connection.send("\r\n");
        connection.recv(50000)
        connection.close()

        request, response = self.master.state.view[0].request, self.master.state.view[0].response
        assert response.code == 304  # sanity test for our low level request
        assert 0.95 < (request.timestamp_end - request.timestamp_start) < 1.2 #time.sleep might be a little bit shorter than a second

    def test_request_timestamps_not_affected_by_client_time(self):
        # test that don't include user wait time in request's timestamps

        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        f = self.pathod("304:b@10k")
        assert f.status_code == 304

        request = self.master.state.view[0].request
        assert request.timestamp_end - request.timestamp_start <= 0.1

        request = self.master.state.view[1].request
        assert request.timestamp_end - request.timestamp_start <= 0.1

    def test_request_tcp_setup_timestamp_presence(self):
        # tests that the first request in a tcp connection has a tcp_setup_timestamp
        # while others do not
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("localhost", self.proxy.port))
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        connection.send("\r\n");
        connection.recv(5000)
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        connection.send("\r\n");
        connection.recv(5000)
        connection.close()

        first_request = self.master.state.view[0].request
        second_request = self.master.state.view[1].request
        assert first_request.tcp_setup_timestamp
        assert first_request.ssl_setup_timestamp == None
        assert second_request.tcp_setup_timestamp == None
        assert second_request.ssl_setup_timestamp == None

    def test_request_ip(self):
        f = self.pathod("200:b@100")
        assert f.status_code == 200
        request = self.master.state.view[0].request
        assert request.ip == "127.0.0.1"

class TestProxySSL(tservers.HTTPProxTest):
    ssl=True
    def test_request_ssl_setup_timestamp_presence(self):
        # tests that the ssl timestamp is present when ssl is used
        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        first_request = self.master.state.view[0].request
        assert first_request.ssl_setup_timestamp

class MasterFakeResponse(tservers.TestMaster):
    def handle_request(self, m):
        resp = tutils.tresp()
        m.reply(resp)


class TestFakeResponse(tservers.HTTPProxTest):
    masterclass = MasterFakeResponse
    def test_fake(self):
        f = self.pathod("200")
        assert "header_response" in f.headers.keys()



class MasterKillRequest(tservers.TestMaster):
    def handle_request(self, m):
        m.reply(proxy.KILL)


class TestKillRequest(tservers.HTTPProxTest):
    masterclass = MasterKillRequest
    def test_kill(self):
        tutils.raises("server disconnect", self.pathod, "200")
        # Nothing should have hit the server
        assert not self.server.last_log()


class MasterKillResponse(tservers.TestMaster):
    def handle_response(self, m):
        m.reply(proxy.KILL)


class TestKillResponse(tservers.HTTPProxTest):
    masterclass = MasterKillResponse
    def test_kill(self):
        tutils.raises("server disconnect", self.pathod, "200")
        # The server should have seen a request
        assert self.server.last_log()


class EResolver(tservers.TResolver):
    def original_addr(self, sock):
        return None


class TestTransparentResolveError(tservers.TransparentProxTest):
    resolver = EResolver
    def test_resolve_error(self):
        assert self.pathod("304").status_code == 502



class MasterIncomplete(tservers.TestMaster):
    def handle_request(self, m):
        resp = tutils.tresp()
        resp.content = flow.CONTENT_MISSING
        m.reply(resp)


class TestIncompleteResponse(tservers.HTTPProxTest):
    masterclass = MasterIncomplete
    def test_incomplete(self):
        assert self.pathod("200").status_code == 502



