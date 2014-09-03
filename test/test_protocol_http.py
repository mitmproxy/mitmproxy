from libmproxy.protocol.http import *
from libmproxy.protocol import KILL
from cStringIO import StringIO
import tutils, tservers


def test_HttpAuthenticationError():
    x = HttpAuthenticationError({"foo": "bar"})
    assert str(x)
    assert "foo" in x.headers


def test_stripped_chunked_encoding_no_content():
    """
    https://github.com/mitmproxy/mitmproxy/issues/186
    """
    r = tutils.tresp(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()

    r = tutils.treq(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()


class TestHTTPRequest:
    def test_asterisk_form(self):
        s = StringIO("OPTIONS * HTTP/1.1")
        f = tutils.tflow(req=None)
        f.request = HTTPRequest.from_stream(s)
        assert f.request.form_in == "relative"
        f.request.host = f.server_conn.address.host
        f.request.port = f.server_conn.address.port
        f.request.scheme = "http"
        assert f.request._assemble() == "OPTIONS * HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_origin_form(self):
        s = StringIO("GET /foo\xff HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)

    def test_authority_form(self):
        s = StringIO("CONNECT oops-no-port.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("CONNECT address:22 HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        r.scheme, r.host, r.port = "http", "address", 22
        assert r._assemble() == "CONNECT address:22 HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_absolute_form(self):
        s = StringIO("GET oops-no-protocol.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("GET http://address:22/ HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r._assemble() == "GET http://address:22/ HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_assemble_unknown_form(self):
        r = tutils.treq()
        tutils.raises("Invalid request form", r._assemble, "antiauthority")

    def test_set_url(self):
        r = tutils.treq_absolute()
        r.url = "https://otheraddress:42/ORLY"
        assert r.scheme == "https"
        assert r.host == "otheraddress"
        assert r.port == 42
        assert r.path == "/ORLY"


class TestHTTPResponse:
    def test_read_from_stringio(self):
        _s = "HTTP/1.1 200 OK\r\n" \
             "Content-Length: 7\r\n" \
             "\r\n"\
             "content\r\n" \
             "HTTP/1.1 204 OK\r\n" \
             "\r\n"
        s = StringIO(_s)
        r = HTTPResponse.from_stream(s, "GET")
        assert r.code == 200
        assert r.content == "content"
        assert HTTPResponse.from_stream(s, "GET").code == 204

        s = StringIO(_s)
        r = HTTPResponse.from_stream(s, "HEAD")  # HEAD must not have content by spec. We should leave it on the pipe.
        assert r.code == 200
        assert r.content == ""
        tutils.raises("Invalid server response: 'content", HTTPResponse.from_stream, s, "GET")


class TestInvalidRequests(tservers.HTTPProxTest):
    ssl = True
    def test_double_connect(self):
        p = self.pathoc()
        r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert "Must not CONNECT on already encrypted connection" in r.content

    def test_relative_request(self):
        p = self.pathoc_raw()
        p.connect()
        r = p.request("get:/p/200")
        assert r.status_code == 400
        assert "Invalid HTTP request form" in r.content


class TestProxyChaining(tservers.HTTPChainProxyTest):
    def test_all(self):
        self.chain[1].tmaster.replacehooks.add("~q", "foo", "bar") # replace in request
        self.chain[0].tmaster.replacehooks.add("~q", "foo", "oh noes!")
        self.proxy.tmaster.replacehooks.add("~q", "bar", "baz")
        self.chain[0].tmaster.replacehooks.add("~s", "baz", "ORLY")  # replace in response

        p = self.pathoc()
        req = p.request("get:'%s/p/418:b\"foo\"'" % self.server.urlbase)
        assert req.content == "ORLY"
        assert req.status_code == 418

class TestProxyChainingSSL(tservers.HTTPChainProxyTest):
    ssl = True
    def test_simple(self):
        p = self.pathoc()
        req = p.request("get:'/p/418:b\"content\"'")
        assert req.content == "content"
        assert req.status_code == 418

        assert self.chain[1].tmaster.state.flow_count() == 2  # CONNECT from pathoc to chain[0],
                                                              # request from pathoc to chain[0]
        assert self.chain[0].tmaster.state.flow_count() == 2  # CONNECT from chain[1] to proxy,
                                                              # request from chain[1] to proxy
        assert self.proxy.tmaster.state.flow_count() == 1  # request from chain[0] (regular proxy doesn't store CONNECTs)

    def test_closing_connect_response(self):
        """
        https://github.com/mitmproxy/mitmproxy/issues/313
        """
        def handle_request(f):
            f.request.httpversion = (1, 0)
            del f.request.headers["Content-Length"]
            f.reply()
        _handle_request = self.chain[0].tmaster.handle_request
        self.chain[0].tmaster.handle_request = handle_request
        try:
            assert self.pathoc().request("get:/p/418").status_code == 418
        finally:
            self.chain[0].tmaster.handle_request = _handle_request

    def test_sni(self):
        p = self.pathoc(sni="foo.com")
        req = p.request("get:'/p/418:b\"content\"'")
        assert req.content == "content"
        assert req.status_code == 418

class TestProxyChainingSSLReconnect(tservers.HTTPChainProxyTest):
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
            def handler(f):
                k[0] += 1
                if not (k[0] in exclude):
                    f.client_conn.finish()
                    f.error = Error("terminated")
                    f.reply(KILL)
                return _func(f)
            setattr(master, attr, handler)

        kill_requests(self.proxy.tmaster, "handle_request",
                      exclude=[
                              # fail first request
                          2,  # allow second request
                      ])

        kill_requests(self.chain[0].tmaster, "handle_request",
                      exclude=[
                          1,  # CONNECT
                              # fail first request
                          3,  # reCONNECT
                          4,  # request
                      ])

        p = self.pathoc()
        req = p.request("get:'/p/418:b\"content\"'")
        assert self.chain[1].tmaster.state.flow_count() == 2  # CONNECT and request
        assert self.chain[0].tmaster.state.flow_count() == 4  # CONNECT, failing request,
                                                              # reCONNECT, request
        assert self.proxy.tmaster.state.flow_count() == 2  # failing request, request
                                                           # (doesn't store (repeated) CONNECTs from chain[0]
                                                           #  as it is a regular proxy)
        assert req.content == "content"
        assert req.status_code == 418

        assert not self.proxy.tmaster.state._flow_list[0].response  # killed
        assert self.proxy.tmaster.state._flow_list[1].response

        assert self.chain[1].tmaster.state._flow_list[0].request.form_in == "authority"
        assert self.chain[1].tmaster.state._flow_list[1].request.form_in == "relative"

        assert self.chain[0].tmaster.state._flow_list[0].request.form_in == "authority"
        assert self.chain[0].tmaster.state._flow_list[1].request.form_in == "relative"
        assert self.chain[0].tmaster.state._flow_list[2].request.form_in == "authority"
        assert self.chain[0].tmaster.state._flow_list[3].request.form_in == "relative"

        assert self.proxy.tmaster.state._flow_list[0].request.form_in == "relative"
        assert self.proxy.tmaster.state._flow_list[1].request.form_in == "relative"

        req = p.request("get:'/p/418:b\"content2\"'")

        assert req.status_code == 502
        assert self.chain[1].tmaster.state.flow_count() == 3  # + new request
        assert self.chain[0].tmaster.state.flow_count() == 6  # + new request, repeated CONNECT from chain[1]
                                                              # (both terminated)
        assert self.proxy.tmaster.state.flow_count() == 2  # nothing happened here
