import pytest

from mitmproxy.connection import ConnectionState, Server
from mitmproxy.flow import Error
from mitmproxy.http import HTTPFlow, Response
from mitmproxy.net.server_spec import ServerSpec
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import CloseConnection, Log, OpenConnection, SendData
from mitmproxy.proxy.events import ConnectionClosed, DataReceived
from mitmproxy.proxy.layers import TCPLayer, http, tls
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.tcp import TcpMessageInjected, TcpStartHook
from mitmproxy.proxy.layers.websocket import WebsocketStartHook
from mitmproxy.tcp import TCPFlow, TCPMessage
from test.mitmproxy.proxy.tutils import Placeholder, Playbook, reply, reply_next_layer


def test_http_proxy(tctx):
    """Test a simple HTTP GET / request"""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client, b"GET http://example.com/foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World")
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            >> DataReceived(server, b"!")
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")
    )
    assert server().address == ("example.com", 80)


@pytest.mark.parametrize("strategy", ["lazy", "eager"])
def test_https_proxy(strategy, tctx):
    """Test a CONNECT request, followed by a HTTP GET /"""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))
    tctx.options.connection_strategy = strategy

    (playbook
     >> DataReceived(tctx.client, b"CONNECT example.proxy:80 HTTP/1.1\r\n\r\n")
     << http.HttpConnectHook(Placeholder())
     >> reply())
    if strategy == "eager":
        (playbook
         << OpenConnection(server)
         >> reply(None))
    (playbook
     << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
     >> DataReceived(tctx.client, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
     << layer.NextLayerHook(Placeholder())
     >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
     << http.HttpRequestHeadersHook(flow)
     >> reply()
     << http.HttpRequestHook(flow)
     >> reply())
    if strategy == "lazy":
        (playbook
         << OpenConnection(server)
         >> reply(None))
    (playbook
     << SendData(server, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
     >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")
     << http.HttpResponseHeadersHook(flow)
     >> reply()
     << http.HttpResponseHook(flow)
     >> reply()
     << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!"))
    assert playbook


@pytest.mark.parametrize("https_client", [False, True])
@pytest.mark.parametrize("https_server", [False, True])
@pytest.mark.parametrize("strategy", ["lazy", "eager"])
def test_redirect(strategy, https_server, https_client, tctx, monkeypatch):
    """Test redirects between http:// and https:// in regular proxy mode."""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    tctx.options.connection_strategy = strategy
    p = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)

    if https_server:
        monkeypatch.setattr(tls, "ServerTLSLayer", tls.MockTLSLayer)

    def redirect(flow: HTTPFlow):
        if https_server:
            flow.request.url = "https://redirected.site/"
        else:
            flow.request.url = "http://redirected.site/"

    if https_client:
        p >> DataReceived(tctx.client, b"CONNECT example.com:80 HTTP/1.1\r\n\r\n")
        if strategy == "eager":
            p << OpenConnection(Placeholder())
            p >> reply(None)
        p << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
        p >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        p << layer.NextLayerHook(Placeholder())
        p >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
    else:
        p >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
    p << http.HttpRequestHook(flow)
    p >> reply(side_effect=redirect)
    p << OpenConnection(server)
    p >> reply(None)
    p << SendData(server, b"GET / HTTP/1.1\r\nHost: redirected.site\r\n\r\n")
    p >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")
    p << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")

    assert p
    if https_server:
        assert server().address == ("redirected.site", 443)
    else:
        assert server().address == ("redirected.site", 80)


def test_multiple_server_connections(tctx):
    """Test multiple requests being rewritten to different targets."""
    server1 = Placeholder(Server)
    server2 = Placeholder(Server)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)

    def redirect(to: str):
        def side_effect(flow: HTTPFlow):
            flow.request.url = to

        return side_effect

    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << http.HttpRequestHook(Placeholder())
            >> reply(side_effect=redirect("http://one.redirect/"))
            << OpenConnection(server1)
            >> reply(None)
            << SendData(server1, b"GET / HTTP/1.1\r\nHost: one.redirect\r\n\r\n")
            >> DataReceived(server1, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << http.HttpRequestHook(Placeholder())
            >> reply(side_effect=redirect("http://two.redirect/"))
            << OpenConnection(server2)
            >> reply(None)
            << SendData(server2, b"GET / HTTP/1.1\r\nHost: two.redirect\r\n\r\n")
            >> DataReceived(server2, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server1().address == ("one.redirect", 80)
    assert server2().address == ("two.redirect", 80)


@pytest.mark.parametrize("transfer_encoding", ["identity", "chunked"])
def test_pipelining(tctx, transfer_encoding):
    """Test that multiple requests can be processed over the same connection"""

    tctx.server.address = ("example.com", 80)
    tctx.server.state = ConnectionState.OPEN

    req = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
    if transfer_encoding == "identity":
        resp = (b"HTTP/1.1 200 OK\r\n"
                b"Content-Length: 12\r\n"
                b"\r\n"
                b"Hello World!")
    else:
        resp = (b"HTTP/1.1 200 OK\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"\r\n"
                b"c\r\n"
                b"Hello World!\r\n"
                b"0\r\n"
                b"\r\n")

    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent), hooks=False)
            # Roundtrip 1
            >> DataReceived(tctx.client, req)
            << SendData(tctx.server, req)
            >> DataReceived(tctx.server, resp)
            << SendData(tctx.client, resp)
            # Roundtrip 2
            >> DataReceived(tctx.client, req)
            << SendData(tctx.server, req)
            >> DataReceived(tctx.server, resp)
            << SendData(tctx.client, resp)
    )


def test_http_reply_from_proxy(tctx):
    """Test a response served by mitmproxy itself."""

    def reply_from_proxy(flow: HTTPFlow):
        flow.response = Response.make(418)

    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << http.HttpRequestHook(Placeholder())
            >> reply(side_effect=reply_from_proxy)
            << SendData(tctx.client, b"HTTP/1.1 418 I'm a teapot\r\ncontent-length: 0\r\n\r\n")
    )


def test_response_until_eof(tctx):
    """Test scenario where the server response body is terminated by EOF."""
    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\n\r\nfoo")
            >> ConnectionClosed(server)
            << CloseConnection(server)
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n\r\nfoo")
            << CloseConnection(tctx.client)
    )


def test_disconnect_while_intercept(tctx):
    """Test a server disconnect while a request is intercepted."""
    tctx.options.connection_strategy = "eager"

    server1 = Placeholder(Server)
    server2 = Placeholder(Server)
    flow = Placeholder(HTTPFlow)

    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"CONNECT example.com:80 HTTP/1.1\r\n\r\n")
            << http.HttpConnectHook(Placeholder(HTTPFlow))
            >> reply()
            << OpenConnection(server1)
            >> reply(None)
            << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << layer.NextLayerHook(Placeholder())
            >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
            << http.HttpRequestHook(flow)
            >> ConnectionClosed(server1)
            << CloseConnection(server1)
            >> reply(to=-3)
            << OpenConnection(server2)
            >> reply(None)
            << SendData(server2, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server2, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server1() != server2()
    assert flow().server_conn == server2()


@pytest.mark.parametrize("why", ["body_size=0", "body_size=3", "addon"])
@pytest.mark.parametrize("transfer_encoding", ["identity", "chunked"])
def test_response_streaming(tctx, why, transfer_encoding):
    """Test HTTP response streaming"""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))

    if why.startswith("body_size"):
        tctx.options.stream_large_bodies = why.replace("body_size=", "")

    def enable_streaming(flow: HTTPFlow):
        if why == "addon":
            flow.response.stream = True

    assert (
        playbook
        >> DataReceived(tctx.client, b"GET http://example.com/largefile HTTP/1.1\r\nHost: example.com\r\n\r\n")
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"GET /largefile HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> DataReceived(server, b"HTTP/1.1 200 OK\r\n")
    )
    if transfer_encoding == "identity":
        playbook >> DataReceived(server, b"Content-Length: 6\r\n\r\n"
                                         b"abc")
    else:
        playbook >> DataReceived(server, b"Transfer-Encoding: chunked\r\n\r\n"
                                         b"3\r\nabc\r\n")

    playbook << http.HttpResponseHeadersHook(flow)
    playbook >> reply(side_effect=enable_streaming)

    if transfer_encoding == "identity":
        playbook << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                          b"Content-Length: 6\r\n\r\n"
                                          b"abc")
        playbook >> DataReceived(server, b"def")
        playbook << SendData(tctx.client, b"def")
    else:
        if why == "body_size=3":
            playbook >> DataReceived(server, b"3\r\ndef\r\n")
            playbook << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                              b"Transfer-Encoding: chunked\r\n\r\n"
                                              b"6\r\nabcdef\r\n")
        else:
            playbook << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                              b"Transfer-Encoding: chunked\r\n\r\n"
                                              b"3\r\nabc\r\n")
            playbook >> DataReceived(server, b"3\r\ndef\r\n")
            playbook << SendData(tctx.client, b"3\r\ndef\r\n")
        playbook >> DataReceived(server, b"0\r\n\r\n")

    playbook << http.HttpResponseHook(flow)
    playbook >> reply()

    if transfer_encoding == "chunked":
        playbook << SendData(tctx.client, b"0\r\n\r\n")

    assert playbook


def test_stream_modify(tctx):
    """Test HTTP stream modification"""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)

    def enable_streaming(flow: HTTPFlow):
        if flow.response is None:
            flow.request.stream = lambda x: b"[" + x + b"]"
        else:
            flow.response.stream = lambda x: b"[" + x + b"]"

    assert (
        Playbook(http.HttpLayer(tctx, HTTPMode.regular))
        >> DataReceived(tctx.client, b"POST http://example.com/ HTTP/1.1\r\n"
                                     b"Host: example.com\r\n"
                                     b"Transfer-Encoding: chunked\r\n\r\n"
                                     b"3\r\nabc\r\n"
                                     b"0\r\n\r\n")
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"POST / HTTP/1.1\r\n"
                            b"Host: example.com\r\n"
                            b"Transfer-Encoding: chunked\r\n\r\n"
                            b"5\r\n[abc]\r\n"
                            b"2\r\n[]\r\n")
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(server, b"0\r\n\r\n")
        >> DataReceived(server, b"HTTP/1.1 200 OK\r\n"
                                b"Transfer-Encoding: chunked\r\n\r\n"
                                b"3\r\ndef\r\n"
                                b"0\r\n\r\n")
        << http.HttpResponseHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                 b"Transfer-Encoding: chunked\r\n\r\n"
                                 b"5\r\n[def]\r\n"
                                 b"2\r\n[]\r\n")
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(tctx.client, b"0\r\n\r\n")
    )


@pytest.mark.parametrize("why", ["body_size=0", "body_size=3", "addon"])
@pytest.mark.parametrize("transfer_encoding", ["identity", "chunked"])
@pytest.mark.parametrize("response", ["normal response", "early response", "early close", "early kill"])
def test_request_streaming(tctx, why, transfer_encoding, response):
    """
    Test HTTP request streaming

    This is a bit more contrived as we may receive server data while we are still sending the request.
    """
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))

    if why.startswith("body_size"):
        tctx.options.stream_large_bodies = why.replace("body_size=", "")

    def enable_streaming(flow: HTTPFlow):
        if why == "addon":
            flow.request.stream = True

    playbook >> DataReceived(tctx.client, b"POST http://example.com/ HTTP/1.1\r\n"
                                          b"Host: example.com\r\n")
    if transfer_encoding == "identity":
        playbook >> DataReceived(tctx.client, b"Content-Length: 9\r\n\r\n"
                                              b"abc")
    else:
        playbook >> DataReceived(tctx.client, b"Transfer-Encoding: chunked\r\n\r\n"
                                              b"3\r\nabc\r\n")

    playbook << http.HttpRequestHeadersHook(flow)
    playbook >> reply(side_effect=enable_streaming)

    needs_more_data_before_open = (why == "body_size=3" and transfer_encoding == "chunked")
    if needs_more_data_before_open:
        playbook >> DataReceived(tctx.client, b"3\r\ndef\r\n")

    playbook << OpenConnection(server)
    playbook >> reply(None)
    playbook << SendData(server, b"POST / HTTP/1.1\r\n"
                                 b"Host: example.com\r\n")

    if transfer_encoding == "identity":
        playbook << SendData(server, b"Content-Length: 9\r\n\r\n"
                                     b"abc")
        playbook >> DataReceived(tctx.client, b"def")
        playbook << SendData(server, b"def")
    else:
        if needs_more_data_before_open:
            playbook << SendData(server, b"Transfer-Encoding: chunked\r\n\r\n"
                                         b"6\r\nabcdef\r\n")
        else:
            playbook << SendData(server, b"Transfer-Encoding: chunked\r\n\r\n"
                                         b"3\r\nabc\r\n")
            playbook >> DataReceived(tctx.client, b"3\r\ndef\r\n")
            playbook << SendData(server, b"3\r\ndef\r\n")

    if response == "normal response":
        if transfer_encoding == "identity":
            playbook >> DataReceived(tctx.client, b"ghi")
            playbook << SendData(server, b"ghi")
        else:
            playbook >> DataReceived(tctx.client, b"3\r\nghi\r\n0\r\n\r\n")
            playbook << SendData(server, b"3\r\nghi\r\n")

        playbook << http.HttpRequestHook(flow)
        playbook >> reply()
        if transfer_encoding == "chunked":
            playbook << SendData(server, b"0\r\n\r\n")
        assert (
            playbook
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        )
    elif response == "early response":
        # We may receive a response before we have finished sending our request.
        # We continue sending unless the server closes the connection.
        # https://tools.ietf.org/html/rfc7231#section-6.5.11
        assert (
            playbook
            >> DataReceived(server, b"HTTP/1.1 413 Request Entity Too Large\r\nContent-Length: 0\r\n\r\n")
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client, b"HTTP/1.1 413 Request Entity Too Large\r\nContent-Length: 0\r\n\r\n")
        )
        if transfer_encoding == "identity":
            playbook >> DataReceived(tctx.client, b"ghi")
            playbook << SendData(server, b"ghi")
        else:
            playbook >> DataReceived(tctx.client, b"3\r\nghi\r\n0\r\n\r\n")
            playbook << SendData(server, b"3\r\nghi\r\n")
        playbook << http.HttpRequestHook(flow)
        playbook >> reply()
        if transfer_encoding == "chunked":
            playbook << SendData(server, b"0\r\n\r\n")
        assert playbook
    elif response == "early close":
        assert (
                playbook
                >> DataReceived(server, b"HTTP/1.1 413 Request Entity Too Large\r\nContent-Length: 0\r\n\r\n")
                << http.HttpResponseHeadersHook(flow)
                >> reply()
                << http.HttpResponseHook(flow)
                >> reply()
                << SendData(tctx.client, b"HTTP/1.1 413 Request Entity Too Large\r\nContent-Length: 0\r\n\r\n")
                >> ConnectionClosed(server)
                << CloseConnection(server)
                << CloseConnection(tctx.client)
        )
    elif response == "early kill":
        err = Placeholder(bytes)
        assert (
                playbook
                >> ConnectionClosed(server)
                << CloseConnection(server)
                << http.HttpErrorHook(flow)
                >> reply()
                << SendData(tctx.client, err)
                << CloseConnection(tctx.client)
        )
        assert b"502 Bad Gateway" in err()
    else:  # pragma: no cover
        assert False


@pytest.mark.parametrize("where", ["request", "response"])
@pytest.mark.parametrize("transfer_encoding", ["identity", "chunked"])
def test_body_size_limit(tctx, where, transfer_encoding):
    """Test HTTP request body_size_limit"""
    tctx.options.body_size_limit = "3"
    err = Placeholder(bytes)
    flow = Placeholder(HTTPFlow)

    if transfer_encoding == "identity":
        body = b"Content-Length: 6\r\n\r\nabcdef"
    else:
        body = b"Transfer-Encoding: chunked\r\n\r\n6\r\nabcdef"

    if where == "request":
        assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client, b"POST http://example.com/ HTTP/1.1\r\n"
                                         b"Host: example.com\r\n" + body)
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpErrorHook(flow)
            >> reply()
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
        )
        assert b"413 Payload Too Large" in err()
        assert b"body_size_limit" in err()
    else:
        server = Placeholder(Server)
        assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\n"
                                         b"Host: example.com\r\n\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\n"
                                b"Host: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\n" + body)
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpErrorHook(flow)
            >> reply()
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
            << CloseConnection(server)
        )
        assert b"502 Bad Gateway" in err()
        assert b"body_size_limit" in err()


@pytest.mark.parametrize("connect", [True, False])
def test_server_unreachable(tctx, connect):
    """Test the scenario where the target server is unreachable."""
    tctx.options.connection_strategy = "eager"
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    err = Placeholder(bytes)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
    if connect:
        playbook >> DataReceived(tctx.client, b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
    else:
        playbook >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\n\r\n")

    playbook << OpenConnection(server)
    playbook >> reply("Connection failed")
    if not connect:
        # Our API isn't ideal here, there is no error hook for CONNECT requests currently.
        # We could fix this either by having CONNECT request go through all our regular hooks,
        # or by adding dedicated ok/error hooks.
        playbook << http.HttpErrorHook(flow)
        playbook >> reply()
    playbook << SendData(tctx.client, err)
    if not connect:
        playbook << CloseConnection(tctx.client)

    assert playbook
    if not connect:
        assert flow().error
    assert b"502 Bad Gateway" in err()
    assert b"Connection failed" in err()


@pytest.mark.parametrize("data", [
    None,
    b"I don't speak HTTP.",
    b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nweee"
])
def test_server_aborts(tctx, data):
    """Test the scenario where the server doesn't serve a response"""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    err = Placeholder(bytes)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    )
    if data:
        playbook >> DataReceived(server, data)
    assert (
            playbook
            >> ConnectionClosed(server)
            << CloseConnection(server)
            << http.HttpErrorHook(flow)
            >> reply()
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
    )
    assert flow().error
    assert b"502 Bad Gateway" in err()


@pytest.mark.parametrize("redirect", ["", "change-destination", "change-proxy"])
@pytest.mark.parametrize("scheme", ["http", "https"])
def test_upstream_proxy(tctx, redirect, scheme):
    """Test that an upstream HTTP proxy is used."""
    server = Placeholder(Server)
    server2 = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    tctx.options.mode = "upstream:http://proxy:8080"
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.upstream), hooks=False)

    if scheme == "http":
        assert (
                playbook
                >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
                << OpenConnection(server)
                >> reply(None)
                << SendData(server, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
        )

    else:
        assert (
                playbook
                >> DataReceived(tctx.client, b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
                << SendData(tctx.client, b"HTTP/1.1 200 Connection established\r\n\r\n")
                >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
                << layer.NextLayerHook(Placeholder())
                >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
                << OpenConnection(server)
                >> reply(None)
                << SendData(server, b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
                >> DataReceived(server, b"HTTP/1.1 200 Connection established\r\n\r\n")
                << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        )

    playbook >> DataReceived(server, b"HTTP/1.1 418 OK\r\nContent-Length: 0\r\n\r\n")
    playbook << SendData(tctx.client, b"HTTP/1.1 418 OK\r\nContent-Length: 0\r\n\r\n")

    assert playbook
    assert server().address == ("proxy", 8080)

    if scheme == "http":
        playbook >> DataReceived(tctx.client, b"GET http://example.com/two HTTP/1.1\r\nHost: example.com\r\n\r\n")
    else:
        playbook >> DataReceived(tctx.client, b"GET /two HTTP/1.1\r\nHost: example.com\r\n\r\n")

    assert (playbook << http.HttpRequestHook(flow))
    if redirect == "change-destination":
        flow().request.host = "other-server"
        flow().request.host_header = "example.com"
    elif redirect == "change-proxy":
        flow().server_conn.via = ServerSpec("http", address=("other-proxy", 1234))
    playbook >> reply()

    if redirect:
        # Protocol-wise we wouldn't need to open a new connection for plain http host redirects,
        # but we disregard this edge case to simplify implementation.
        playbook << OpenConnection(server2)
        playbook >> reply(None)
    else:
        server2 = server

    if scheme == "http":
        if redirect == "change-destination":
            playbook << SendData(server2, b"GET http://other-server/two HTTP/1.1\r\nHost: example.com\r\n\r\n")
        else:
            playbook << SendData(server2, b"GET http://example.com/two HTTP/1.1\r\nHost: example.com\r\n\r\n")
    else:
        if redirect == "change-destination":
            playbook << SendData(server2, b"CONNECT other-server:443 HTTP/1.1\r\n\r\n")
            playbook >> DataReceived(server2, b"HTTP/1.1 200 Connection established\r\n\r\n")
        elif redirect == "change-proxy":
            playbook << SendData(server2, b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
            playbook >> DataReceived(server2, b"HTTP/1.1 200 Connection established\r\n\r\n")
        playbook << SendData(server2, b"GET /two HTTP/1.1\r\nHost: example.com\r\n\r\n")

    playbook >> DataReceived(server2, b"HTTP/1.1 418 OK\r\nContent-Length: 0\r\n\r\n")
    playbook << SendData(tctx.client, b"HTTP/1.1 418 OK\r\nContent-Length: 0\r\n\r\n")

    assert playbook

    if redirect == "change-proxy":
        assert server2().address == ("other-proxy", 1234)
    else:
        assert server2().address == ("proxy", 8080)

    assert (
            playbook
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.client)
    )


@pytest.mark.parametrize("mode", ["regular", "upstream"])
@pytest.mark.parametrize("close_first", ["client", "server"])
def test_http_proxy_tcp(tctx, mode, close_first):
    """Test TCP over HTTP CONNECT."""
    server = Placeholder(Server)
    f = Placeholder(TCPFlow)
    tctx.options.connection_strategy = "lazy"

    if mode == "upstream":
        tctx.options.mode = "upstream:http://proxy:8080"
        toplayer = http.HttpLayer(tctx, HTTPMode.upstream)
    else:
        tctx.options.mode = "regular"
        toplayer = http.HttpLayer(tctx, HTTPMode.regular)

    playbook = Playbook(toplayer, hooks=False)
    assert (
            playbook
            >> DataReceived(tctx.client, b"CONNECT example:443 HTTP/1.1\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 Connection established\r\n\r\n")
            >> DataReceived(tctx.client, b"this is not http")
            << layer.NextLayerHook(Placeholder())
            >> reply_next_layer(lambda ctx: TCPLayer(ctx, ignore=False))
            << TcpStartHook(f)
            >> reply()
            << OpenConnection(server)
    )

    playbook >> reply(None)
    if mode == "upstream":
        playbook << SendData(server, b"CONNECT example:443 HTTP/1.1\r\n\r\n")
        playbook >> DataReceived(server, b"HTTP/1.1 200 Connection established\r\n\r\n")

    assert (
            playbook
            << SendData(server, b"this is not http")
            >> DataReceived(server, b"true that")
            << SendData(tctx.client, b"true that")
    )

    if mode == "regular":
        assert server().address == ("example", 443)
    else:
        assert server().address == ("proxy", 8080)

    assert (
        playbook
        >> TcpMessageInjected(f, TCPMessage(False, b"fake news from your friendly man-in-the-middle"))
        << SendData(tctx.client, b"fake news from your friendly man-in-the-middle")
    )

    if close_first == "client":
        a, b = tctx.client, server
    else:
        a, b = server, tctx.client
    assert (
            playbook
            >> ConnectionClosed(a)
            << CloseConnection(b)
            >> ConnectionClosed(b)
            << CloseConnection(a)
    )


@pytest.mark.parametrize("strategy", ["eager", "lazy"])
def test_proxy_chain(tctx, strategy):
    server = Placeholder(Server)
    tctx.options.connection_strategy = strategy
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)

    playbook >> DataReceived(tctx.client, b"CONNECT proxy:8080 HTTP/1.1\r\n\r\n")
    if strategy == "eager":
        playbook << OpenConnection(server)
        playbook >> reply(None)
    playbook << SendData(tctx.client, b"HTTP/1.1 200 Connection established\r\n\r\n")

    playbook >> DataReceived(tctx.client, b"CONNECT second-proxy:8080 HTTP/1.1\r\n\r\n")
    playbook << layer.NextLayerHook(Placeholder())
    playbook >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
    playbook << SendData(tctx.client,
                         b"HTTP/1.1 502 Bad Gateway\r\n"
                         b"content-length: 198\r\n"
                         b"\r\n"
                         b"mitmproxy received an HTTP CONNECT request even though it is not running in regular/upstream mode. "
                         b"This usually indicates a misconfiguration, please see the mitmproxy mode documentation for details.")

    assert playbook


def test_no_headers(tctx):
    """Test that we can correctly reassemble requests/responses with no headers."""
    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 204 No Content\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 204 No Content\r\n\r\n")
    )
    assert server().address == ("example.com", 80)


def test_http_proxy_relative_request(tctx):
    """Test handling of a relative-form "GET /" in regular proxy mode."""
    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 204 No Content\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 204 No Content\r\n\r\n")
    )
    assert server().address == ("example.com", 80)


def test_http_proxy_relative_request_no_host_header(tctx):
    """Test handling of a relative-form "GET /" in regular proxy mode, but without a host header."""
    err = Placeholder(bytes)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\n\r\n")
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
    )
    assert b"400 Bad Request" in err()
    assert b"HTTP request has no host header, destination unknown." in err()


def test_http_expect(tctx):
    """Test handling of a 'Expect: 100-continue' header."""
    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"PUT http://example.com/large-file HTTP/1.1\r\n"
                                         b"Host: example.com\r\n"
                                         b"Content-Length: 15\r\n"
                                         b"Expect: 100-continue\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 100 Continue\r\n\r\n")
            >> DataReceived(tctx.client, b"lots of content")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"PUT /large-file HTTP/1.1\r\n"
                                b"Host: example.com\r\n"
                                b"Content-Length: 15\r\n\r\n"
                                b"lots of content")
            >> DataReceived(server, b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\n\r\n")
    )
    assert server().address == ("example.com", 80)


@pytest.mark.parametrize("stream", [True, False])
def test_http_client_aborts(tctx, stream):
    """Test handling of the case where a client aborts during request transmission."""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=True)

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = True

    assert (
            playbook
            >> DataReceived(tctx.client, b"POST http://example.com/ HTTP/1.1\r\n"
                                         b"Host: example.com\r\n"
                                         b"Content-Length: 6\r\n"
                                         b"\r\n"
                                         b"abc")
            << http.HttpRequestHeadersHook(flow)
    )
    if stream:
        assert (
                playbook
                >> reply(side_effect=enable_streaming)
                << OpenConnection(server)
                >> reply(None)
                << SendData(server, b"POST / HTTP/1.1\r\n"
                                    b"Host: example.com\r\n"
                                    b"Content-Length: 6\r\n"
                                    b"\r\n"
                                    b"abc")
        )
    else:
        assert playbook >> reply()
    (
            playbook
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.client)
    )
    if stream:
        playbook << CloseConnection(server)
    assert (
            playbook
            << http.HttpErrorHook(flow)
            >> reply()
            << None
    )

    assert "peer closed connection" in flow().error.msg


@pytest.mark.parametrize("stream", [True, False])
def test_http_server_aborts(tctx, stream):
    """Test handling of the case where a server aborts during response transmission."""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))

    def enable_streaming(flow: HTTPFlow):
        flow.response.stream = True

    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\n"
                                         b"Host: example.com\r\n\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\n"
                                b"Host: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\n"
                                    b"Content-Length: 6\r\n"
                                    b"\r\n"
                                    b"abc")
            << http.HttpResponseHeadersHook(flow)
    )
    if stream:
        assert (
                playbook
                >> reply(side_effect=enable_streaming)
                << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                         b"Content-Length: 6\r\n"
                                         b"\r\n"
                                         b"abc")
        )
    else:
        assert playbook >> reply()
    assert (
            playbook
            >> ConnectionClosed(server)
            << CloseConnection(server)
            << http.HttpErrorHook(flow)
    )
    if stream:
        assert (
                playbook
                >> reply()
                << CloseConnection(tctx.client)
        )
    else:
        error_html = Placeholder(bytes)
        assert (
                playbook
                >> reply()
                << SendData(tctx.client, error_html)
                << CloseConnection(tctx.client)
        )
        assert b"502 Bad Gateway" in error_html()
        assert b"peer closed connection" in error_html()

    assert "peer closed connection" in flow().error.msg


@pytest.mark.parametrize("when", ["http_connect", "requestheaders", "request", "script-response-responseheaders",
                                  "responseheaders",
                                  "response", "error"])
def test_kill_flow(tctx, when):
    """Test that we properly kill flows if instructed to do so"""
    tctx.options.connection_strategy = "lazy"
    server = Placeholder(Server)
    connect_flow = Placeholder(HTTPFlow)
    flow = Placeholder(HTTPFlow)

    def kill(flow: HTTPFlow):
        # Can't use flow.kill() here because that currently still depends on a reply object.
        flow.error = Error(Error.KILLED_MESSAGE)

    def assert_kill(err_hook: bool = True):
        playbook >> reply(side_effect=kill)
        if err_hook:
            playbook << http.HttpErrorHook(flow)
            playbook >> reply()
        playbook << CloseConnection(tctx.client)
        assert playbook

    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))
    assert (playbook
            >> DataReceived(tctx.client, b"CONNECT example.com:80 HTTP/1.1\r\n\r\n")
            << http.HttpConnectHook(connect_flow))
    if when == "http_connect":
        return assert_kill(False)
    assert (playbook
            >> reply()
            << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
            >> DataReceived(tctx.client, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << layer.NextLayerHook(Placeholder())
            >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
            << http.HttpRequestHeadersHook(flow))
    if when == "requestheaders":
        return assert_kill()
    assert (playbook
            >> reply()
            << http.HttpRequestHook(flow))
    if when == "request":
        return assert_kill()
    if when == "script-response-responseheaders":
        assert (playbook
                >> reply(side_effect=lambda f: setattr(f, "response", Response.make()))
                << http.HttpResponseHeadersHook(flow))
        return assert_kill()
    assert (playbook
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World")
            << http.HttpResponseHeadersHook(flow))
    if when == "responseheaders":
        return assert_kill()

    if when == "response":
        assert (playbook
                >> reply()
                >> DataReceived(server, b"!")
                << http.HttpResponseHook(flow))
        return assert_kill(False)
    elif when == "error":
        assert (playbook
                >> reply()
                >> ConnectionClosed(server)
                << CloseConnection(server)
                << http.HttpErrorHook(flow))
        return assert_kill(False)
    else:
        raise AssertionError


def test_close_during_connect_hook(tctx):
    flow = Placeholder(HTTPFlow)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client,
                            b'CONNECT hi.ls:443 HTTP/1.1\r\n'
                            b'Proxy-Connection: keep-alive\r\n'
                            b'Connection: keep-alive\r\n'
                            b'Host: hi.ls:443\r\n\r\n')
            << http.HttpConnectHook(flow)
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.client)
            >> reply(to=-3)
    )


@pytest.mark.parametrize("client_close", [b"", b"Connection: close\r\n"])
@pytest.mark.parametrize("server_close", [b"", b"Connection: close\r\n"])
def test_connection_close_header(tctx, client_close, server_close):
    """Test that we correctly close connections if we have a `Connection: close` header."""
    if not client_close and not server_close:
        return
    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example/ HTTP/1.1\r\n"
                                         b"Host: example\r\n" + client_close +
                            b"\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\n"
                                b"Host: example\r\n" + client_close +
                        b"\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\n"
                                    b"Content-Length: 0\r\n" + server_close +
                            b"\r\n")
            << CloseConnection(server)
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                     b"Content-Length: 0\r\n" + server_close +
                        b"\r\n")
            << CloseConnection(tctx.client)
    )


@pytest.mark.parametrize("proto", ["websocket", "tcp", "none"])
def test_upgrade(tctx, proto):
    """Test a HTTP -> WebSocket upgrade with different protocols enabled"""
    if proto != "websocket":
        tctx.options.websocket = False
    if proto != "tcp":
        tctx.options.rawtcp = False

    tctx.server.address = ("example.com", 80)
    tctx.server.state = ConnectionState.OPEN
    http_flow = Placeholder(HTTPFlow)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.transparent))
    (
            playbook
            >> DataReceived(tctx.client,
                            b"GET / HTTP/1.1\r\n"
                            b"Connection: upgrade\r\n"
                            b"Upgrade: websocket\r\n"
                            b"Sec-WebSocket-Version: 13\r\n"
                            b"\r\n")
            << http.HttpRequestHeadersHook(http_flow)
            >> reply()
            << http.HttpRequestHook(http_flow)
            >> reply()
            << SendData(tctx.server, b"GET / HTTP/1.1\r\n"
                                     b"Connection: upgrade\r\n"
                                     b"Upgrade: websocket\r\n"
                                     b"Sec-WebSocket-Version: 13\r\n"
                                     b"\r\n")
            >> DataReceived(tctx.server, b"HTTP/1.1 101 Switching Protocols\r\n"
                                         b"Upgrade: websocket\r\n"
                                         b"Connection: Upgrade\r\n"
                                         b"\r\n")
            << http.HttpResponseHeadersHook(http_flow)
            >> reply()
            << http.HttpResponseHook(http_flow)
            >> reply()
            << SendData(tctx.client, b"HTTP/1.1 101 Switching Protocols\r\n"
                                     b"Upgrade: websocket\r\n"
                                     b"Connection: Upgrade\r\n"
                                     b"\r\n")
    )
    if proto == "websocket":
        assert playbook << WebsocketStartHook(http_flow)
    elif proto == "tcp":
        assert playbook << TcpStartHook(Placeholder(TCPFlow))
    else:
        assert (
            playbook
            << Log("Sent HTTP 101 response, but no protocol is enabled to upgrade to.", "warn")
            << CloseConnection(tctx.client)
        )


def test_dont_reuse_closed(tctx):
    """Test that a closed connection is not reused."""
    server = Placeholder(Server)
    server2 = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            >> ConnectionClosed(server)
            << CloseConnection(server)
            >> DataReceived(tctx.client, b"GET http://example.com/two HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server2)
            >> reply(None)
            << SendData(server2, b"GET /two HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server2, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )


def test_reuse_error(tctx):
    """Test that an errored connection is reused."""
    tctx.server.address = ("example.com", 443)
    tctx.server.error = "tls verify failed"
    error_html = Placeholder(bytes)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent), hooks=False)
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\n\r\n")
            << SendData(tctx.client, error_html)
            << CloseConnection(tctx.client)
    )
    assert b"502 Bad Gateway" in error_html()
    assert b"tls verify failed" in error_html()


def test_transparent_sni(tctx):
    """Test that we keep the SNI in lazy transparent mode."""
    tctx.client.sni = "example.com"
    tctx.server.address = ("192.0.2.42", 443)
    tctx.server.tls = True

    flow = Placeholder(HTTPFlow)

    server = Placeholder(Server)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent))
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\n\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
    )
    assert server().address == ("192.0.2.42", 443)
    assert server().sni == "example.com"


def test_original_server_disconnects(tctx):
    """Test that we correctly handle the case where the initial server conn is just closed."""
    tctx.server.state = ConnectionState.OPEN
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent))
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.server)
    )


def test_request_smuggling(tctx):
    """Test that we reject request smuggling"""
    err = Placeholder(bytes)
    assert (
        Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
        >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\n"
                                     b"Host: example.com\r\n"
                                     b"Content-Length: 42\r\n"
                                     b"Transfer-Encoding: chunked\r\n\r\n")
        << SendData(tctx.client, err)
        << CloseConnection(tctx.client)
    )
    assert b"Received both a Transfer-Encoding and a Content-Length header" in err()


def test_request_smuggling_te_te(tctx):
    """Test that we reject transfer-encoding headers that are weird in some way"""
    err = Placeholder(bytes)
    assert (
        Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
        >> DataReceived(tctx.client, ("GET http://example.com/ HTTP/1.1\r\n"
                                      "Host: example.com\r\n"
                                      "Transfer-Encoding: chunKed\r\n\r\n").encode())  # note the non-standard "K"
        << SendData(tctx.client, err)
        << CloseConnection(tctx.client)
    )
    assert b"Invalid transfer encoding" in err()


def test_chunked_and_content_length_set_by_addon(tctx):
    """Test that we don't crash when an addon sets a transfer-encoding header

    We reject a request with both transfer-encoding and content-length header to
    thwart request smuggling, but if a user explicitly sets it we should not crash.
    """
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)

    def make_chunked(flow: HTTPFlow):
        if flow.response:
            flow.response.headers["Transfer-Encoding"] = "chunked"
        else:
            flow.request.headers["Transfer-Encoding"] = "chunked"

    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client, b"POST http://example.com/ HTTP/1.1\r\n"
                                         b"Host: example.com\r\n"
                                         b"Content-Length: 0\r\n\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply(side_effect=make_chunked)
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"POST / HTTP/1.1\r\n"
                                b"Host: example.com\r\n"
                                b"Content-Length: 0\r\n"
                                b"Transfer-Encoding: chunked\r\n\r\n"
                                b"0\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
            >> reply(side_effect=make_chunked)
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\n"
                                     b"Content-Length: 0\r\n"
                                     b"Transfer-Encoding: chunked\r\n\r\n"
                                     b"0\r\n\r\n")
    )
