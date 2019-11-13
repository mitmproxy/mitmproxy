import pytest

from mitmproxy.http import HTTPResponse
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2.commands import Hook, OpenConnection, SendData
from mitmproxy.proxy2.events import ConnectionClosed, DataReceived
from mitmproxy.proxy2.layers import tls
from mitmproxy.proxy2.layers.http import http
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply, reply_establish_server_tls, reply_next_layer


def test_http_proxy(tctx):
    """Test a simple HTTP GET / request"""
    server = Placeholder()
    flow = Placeholder()
    assert (
            Playbook(http.HTTPLayer(tctx, HTTPMode.regular))
            >> DataReceived(tctx.client, b"GET http://example.com/foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << Hook("requestheaders", flow)
            >> reply()
            << Hook("request", flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World")
            << Hook("responseheaders", flow)
            >> reply()
            >> DataReceived(server, b"!")
            << Hook("response", flow)
            >> reply()
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")
    )
    assert server().address == ("example.com", 80)


@pytest.mark.parametrize("strategy", ["lazy", "eager"])
def test_https_proxy(strategy, tctx):
    """Test a CONNECT request, followed by a HTTP GET /"""
    server = Placeholder()
    flow = Placeholder()
    playbook = Playbook(http.HTTPLayer(tctx, HTTPMode.regular))
    tctx.options.connection_strategy = strategy

    (playbook
     >> DataReceived(tctx.client, b"CONNECT example.proxy:80 HTTP/1.1\r\n\r\n")
     << Hook("http_connect", Placeholder())
     >> reply())
    if strategy == "eager":
        (playbook
         << OpenConnection(server)
         >> reply(None))
    (playbook
     << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
     >> DataReceived(tctx.client, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
     << Hook("next_layer", Placeholder())
     >> reply_next_layer(lambda ctx: http.HTTPLayer(ctx, HTTPMode.transparent))
     << Hook("requestheaders", flow)
     >> reply()
     << Hook("request", flow)
     >> reply())
    if strategy == "lazy":
        (playbook
         << OpenConnection(server)
         >> reply(None))
    (playbook
     << SendData(server, b"GET /foo?hello=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
     >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!")
     << Hook("responseheaders", flow)
     >> reply()
     << Hook("response", flow)
     >> reply()
     << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello World!"))
    assert playbook


@pytest.mark.parametrize("https_client", [False, True])
@pytest.mark.parametrize("https_server", [False, True])
@pytest.mark.parametrize("strategy", ["lazy", "eager"])
def test_redirect(strategy, https_server, https_client, tctx):
    """Test redirects between http:// and https:// in regular proxy mode."""
    server = Placeholder()
    flow = Placeholder()
    tctx.options.connection_strategy = strategy
    p = Playbook(http.HTTPLayer(tctx, HTTPMode.regular), hooks=False)

    def redirect(hook: Hook):
        if https_server:
            hook.data.request.url = "https://redirected.site/"
        else:
            hook.data.request.url = "http://redirected.site/"

    if https_client:
        p >> DataReceived(tctx.client, b"CONNECT example.com:80 HTTP/1.1\r\n\r\n")
        if strategy == "eager":
            p << OpenConnection(Placeholder())
            p >> reply(None)
        p << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
        p >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        p << Hook("next_layer", Placeholder())
        p >> reply_next_layer(lambda ctx: http.HTTPLayer(ctx, HTTPMode.transparent))
    else:
        p >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
    p << Hook("request", flow)
    p >> reply(side_effect=redirect)
    p << OpenConnection(server)
    p >> reply(None)
    if https_server:
        p << tls.EstablishServerTLS(server)
        p >> reply_establish_server_tls()
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
    server1 = Placeholder()
    server2 = Placeholder()

    def redirect(to: str):
        def side_effect(hook: Hook):
            hook.data.request.url = to

        return side_effect

    assert (
            Playbook(http.HTTPLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << Hook("request", Placeholder())
            >> reply(side_effect=redirect("http://one.redirect/"))
            << OpenConnection(server1)
            >> reply(None)
            << SendData(server1, b"GET / HTTP/1.1\r\nHost: one.redirect\r\n\r\n")
            >> DataReceived(server1, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << Hook("request", Placeholder())
            >> reply(side_effect=redirect("http://two.redirect/"))
            << OpenConnection(server2)
            >> reply(None)
            << SendData(server2, b"GET / HTTP/1.1\r\nHost: two.redirect\r\n\r\n")
            >> DataReceived(server2, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server1().address == ("one.redirect", 80)
    assert server2().address == ("two.redirect", 80)


def test_http_reply_from_proxy(tctx):
    """Test a response served by mitmproxy itself."""

    def reply_from_proxy(hook: Hook):
        hook.data.response = HTTPResponse.make(418)

    assert (
            Playbook(http.HTTPLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << Hook("request", Placeholder())
            >> reply(side_effect=reply_from_proxy)
            << SendData(tctx.client, b"HTTP/1.1 418 I'm a teapot\r\ncontent-length: 0\r\n\r\n")
    )


def test_disconnect_while_intercept(tctx):
    """Test a server disconnect while a request is intercepted."""
    tctx.options.connection_strategy = "eager"

    server1 = Placeholder()
    server2 = Placeholder()
    flow = Placeholder()

    assert (
            Playbook(http.HTTPLayer(tctx, HTTPMode.regular), hooks=False)
            >> DataReceived(tctx.client, b"CONNECT example.com:80 HTTP/1.1\r\n\r\n")
            << Hook("http_connect", Placeholder())
            >> reply()
            << OpenConnection(server1)
            >> reply(None)
            << SendData(tctx.client, b'HTTP/1.1 200 Connection established\r\n\r\n')
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << Hook("next_layer", Placeholder())
            >> reply_next_layer(lambda ctx: http.HTTPLayer(ctx, HTTPMode.transparent))
            << Hook("request", flow)
            >> ConnectionClosed(server1)
            >> reply(to=-2)
            << OpenConnection(server2)
            >> reply(None)
            << SendData(server2, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
            >> DataReceived(server2, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server1() != server2()
    assert flow().server_conn == server2()
