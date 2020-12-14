import copy

import pytest

from mitmproxy import platform
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.commands import CloseConnection, OpenConnection, SendData, GetSocket, Log
from mitmproxy.proxy.context import Client, Context, Server
from mitmproxy.proxy.events import DataReceived, ConnectionClosed
from mitmproxy.proxy.layer import NextLayer, NextLayerHook
from mitmproxy.proxy.layers import http, modes, tcp, tls
from mitmproxy.proxy.layers.tcp import TcpStartHook, TcpMessageHook
from mitmproxy.proxy.layers.tls import ClientTLSLayer, TlsStartHook
from mitmproxy.tcp import TCPFlow
from test.mitmproxy.proxy.layers.test_tls import reply_tls_start
from test.mitmproxy.proxy.tutils import Placeholder, Playbook, reply, reply_next_layer


def test_upstream_https(tctx):
    """
    Test mitmproxy in HTTPS upstream mode with another mitmproxy instance upstream.
    In other words:

    mitmdump --mode upstream:https://localhost:8081 --ssl-insecure
    mitmdump -p 8081
    curl -x localhost:8080 -k http://example.com
    """
    tctx1 = Context(
        Client(
            ("client", 1234),
            ("127.0.0.1", 8080),
            1605699329
        ),
        copy.deepcopy(tctx.options)
    )
    tctx1.options.mode = "upstream:https://example.mitmproxy.org:8081"
    tctx2 = Context(
        Client(
            ("client", 4321),
            ("127.0.0.1", 8080),
            1605699329
        ),
        copy.deepcopy(tctx.options)
    )
    assert tctx2.options.mode == "regular"
    del tctx

    proxy1 = Playbook(modes.HttpProxy(tctx1), hooks=False)
    proxy2 = Playbook(modes.HttpProxy(tctx2), hooks=False)

    upstream = Placeholder(Server)
    server = Placeholder(Server)
    clienthello = Placeholder(bytes)
    serverhello = Placeholder(bytes)
    request = Placeholder(bytes)
    tls_finished = Placeholder(bytes)
    h2_client_settings_ack = Placeholder(bytes)
    response = Placeholder(bytes)
    h2_server_settings_ack = Placeholder(bytes)

    assert (
            proxy1
            >> DataReceived(tctx1.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.upstream))
            << OpenConnection(upstream)
            >> reply(None)
            << TlsStartHook(Placeholder())
            >> reply_tls_start(alpn=b"h2")
            << SendData(upstream, clienthello)
    )
    assert upstream().address == ("example.mitmproxy.org", 8081)
    assert (
            proxy2
            >> DataReceived(tctx2.client, clienthello())
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(ClientTLSLayer)
            << TlsStartHook(Placeholder())
            >> reply_tls_start(alpn=b"h2")
            << SendData(tctx2.client, serverhello)
    )
    assert (
            proxy1
            >> DataReceived(upstream, serverhello())
            << SendData(upstream, request)
    )
    assert (
            proxy2
            >> DataReceived(tctx2.client, request())
            << SendData(tctx2.client, tls_finished)
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.regular))
            << SendData(tctx2.client, h2_client_settings_ack)
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b'GET / HTTP/1.1\r\nhost: example.com\r\n\r\n')
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << CloseConnection(server)
            << SendData(tctx2.client, response)
    )
    assert server().address == ("example.com", 80)

    assert (
            proxy1
            >> DataReceived(upstream, tls_finished() + h2_client_settings_ack() + response())
            << SendData(upstream, h2_server_settings_ack)
            << SendData(tctx1.client, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
    )


@pytest.mark.parametrize("keep_host_header", [True, False])
def test_reverse_proxy(tctx, keep_host_header):
    """Test mitmproxy in reverse proxy mode.

     - make sure that we connect to the right host
     - make sure that we respect keep_host_header
     - make sure that we include non-standard ports in the host header (#4280)
    """
    server = Placeholder(Server)
    tctx.options.mode = "reverse:http://localhost:8000"
    tctx.options.keep_host_header = keep_host_header
    assert (
            Playbook(modes.ReverseProxy(tctx), hooks=False)
            >> DataReceived(tctx.client, b"GET /foo HTTP/1.1\r\n"
                                         b"Host: example.com\r\n\r\n")
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET /foo HTTP/1.1\r\n"
                                b"Host: " + (b"example.com" if keep_host_header else b"localhost:8000") + b"\r\n\r\n")
            >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server().address == ("localhost", 8000)


@pytest.mark.parametrize("patch", [True, False])
@pytest.mark.parametrize("connection_strategy", ["eager", "lazy"])
def test_reverse_proxy_tcp_over_tls(tctx: Context, monkeypatch, patch, connection_strategy):
    """
    Test
        client --TCP-- mitmproxy --TCP over TLS-- server
    reverse proxying.
    """

    if patch:
        monkeypatch.setattr(tls, "ServerTLSLayer", tls.MockTLSLayer)

    flow = Placeholder(TCPFlow)
    data = Placeholder(bytes)
    tctx.options.mode = "reverse:https://localhost:8000"
    tctx.options.connection_strategy = connection_strategy
    playbook = Playbook(modes.ReverseProxy(tctx))
    if connection_strategy == "eager":
        (
                playbook
                << OpenConnection(tctx.server)
                >> DataReceived(tctx.client, b"\x01\x02\x03")
                >> reply(None, to=OpenConnection(tctx.server))
        )
    else:
        (
                playbook
                >> DataReceived(tctx.client, b"\x01\x02\x03")
        )
    if patch:
        (
                playbook
                << NextLayerHook(Placeholder(NextLayer))
                >> reply_next_layer(tcp.TCPLayer)
                << TcpStartHook(flow)
                >> reply()
        )
        if connection_strategy == "lazy":
            (
                    playbook
                    << OpenConnection(tctx.server)
                    >> reply(None)
            )
        assert (
                playbook
                << TcpMessageHook(flow)
                >> reply()
                << SendData(tctx.server, data)
        )
        assert data() == b"\x01\x02\x03"
    else:
        if connection_strategy == "lazy":
            (
                    playbook
                    << NextLayerHook(Placeholder(NextLayer))
                    >> reply_next_layer(tcp.TCPLayer)
                    << TcpStartHook(flow)
                    >> reply()
                    << OpenConnection(tctx.server)
                    >> reply(None)
            )
        assert (
                playbook
                << TlsStartHook(Placeholder())
                >> reply_tls_start()
                << SendData(tctx.server, data)
        )
        assert tls.parse_client_hello(data()).sni == b"localhost"


@pytest.mark.parametrize("connection_strategy", ["eager", "lazy"])
def test_transparent_tcp(tctx: Context, monkeypatch, connection_strategy):
    monkeypatch.setattr(platform, "original_addr", lambda sock: ("address", 22))

    flow = Placeholder(TCPFlow)
    tctx.options.connection_strategy = connection_strategy

    sock = object()
    playbook = Playbook(modes.TransparentProxy(tctx))
    (
            playbook
            << GetSocket(tctx.client)
            >> reply(sock)
    )
    if connection_strategy == "lazy":
        assert playbook
    else:
        assert (
                playbook
                << OpenConnection(tctx.server)
                >> reply(None)
                >> DataReceived(tctx.server, b"hello")
                << NextLayerHook(Placeholder(NextLayer))
                >> reply_next_layer(tcp.TCPLayer)
                << TcpStartHook(flow)
                >> reply()
                << TcpMessageHook(flow)
                >> reply()
                << SendData(tctx.client, b"hello")
        )
        assert flow().messages[0].content == b"hello"
        assert not flow().messages[0].from_client

    assert tctx.server.address == ("address", 22)


def test_transparent_failure(tctx: Context, monkeypatch):
    """Test that we recover from a transparent mode resolve error."""

    def raise_err(sock):
        raise RuntimeError("platform-specific error")

    monkeypatch.setattr(platform, "original_addr", raise_err)
    assert (
            Playbook(modes.TransparentProxy(tctx), logs=True)
            << GetSocket(tctx.client)
            >> reply(object())
            << Log("Transparent mode failure: RuntimeError('platform-specific error')", "info")
    )


def test_reverse_eager_connect_failure(tctx: Context):
    """
    Test
        client --TCP-- mitmproxy --TCP over TLS-- server
    reverse proxying.
    """

    tctx.options.mode = "reverse:https://localhost:8000"
    tctx.options.connection_strategy = "eager"
    playbook = Playbook(modes.ReverseProxy(tctx))
    assert (
            playbook
            << OpenConnection(tctx.server)
            >> reply("IPoAC unstable")
            << CloseConnection(tctx.client)
            >> ConnectionClosed(tctx.client)
    )
