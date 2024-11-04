import copy

import pytest

from mitmproxy import dns
from mitmproxy.addons.proxyauth import ProxyAuth
from mitmproxy.connection import Client
from mitmproxy.connection import ConnectionState
from mitmproxy.connection import Server
from mitmproxy.proxy import layers
from mitmproxy.proxy.commands import CloseConnection
from mitmproxy.proxy.commands import Log
from mitmproxy.proxy.commands import OpenConnection
from mitmproxy.proxy.commands import RequestWakeup
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import ConnectionClosed
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layer import NextLayer
from mitmproxy.proxy.layer import NextLayerHook
from mitmproxy.proxy.layers import http
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers import quic
from mitmproxy.proxy.layers import tcp
from mitmproxy.proxy.layers import tls
from mitmproxy.proxy.layers import udp
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.tcp import TcpMessageHook
from mitmproxy.proxy.layers.tcp import TcpStartHook
from mitmproxy.proxy.layers.tls import ClientTLSLayer
from mitmproxy.proxy.layers.tls import TlsStartClientHook
from mitmproxy.proxy.layers.tls import TlsStartServerHook
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.tcp import TCPFlow
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.udp import UDPFlow
from test.mitmproxy.proxy.layers.test_tls import reply_tls_start_client
from test.mitmproxy.proxy.layers.test_tls import reply_tls_start_server
from test.mitmproxy.proxy.tutils import Placeholder
from test.mitmproxy.proxy.tutils import Playbook
from test.mitmproxy.proxy.tutils import reply
from test.mitmproxy.proxy.tutils import reply_next_layer


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
            peername=("client", 1234),
            sockname=("127.0.0.1", 8080),
            timestamp_start=1605699329,
            state=ConnectionState.OPEN,
        ),
        copy.deepcopy(tctx.options),
    )
    tctx1.client.proxy_mode = ProxyMode.parse(
        "upstream:https://example.mitmproxy.org:8081"
    )
    tctx2 = Context(
        Client(
            peername=("client", 4321),
            sockname=("127.0.0.1", 8080),
            timestamp_start=1605699329,
            state=ConnectionState.OPEN,
        ),
        copy.deepcopy(tctx.options),
    )
    assert tctx2.client.proxy_mode == ProxyMode.parse("regular")
    del tctx

    proxy1 = Playbook(modes.HttpUpstreamProxy(tctx1), hooks=False)
    proxy2 = Playbook(modes.HttpProxy(tctx2), hooks=False)

    upstream = Placeholder(Server)
    server = Placeholder(Server)
    clienthello = Placeholder(bytes)
    serverhello = Placeholder(bytes)
    request = Placeholder(bytes)
    tls_finished = Placeholder(bytes)
    response = Placeholder(bytes)

    assert (
        proxy1
        >> DataReceived(
            tctx1.client,
            b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n",
        )
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.upstream))
        << OpenConnection(upstream)
        >> reply(None)
        << TlsStartServerHook(Placeholder())
        >> reply_tls_start_server(alpn=b"http/1.1")
        << SendData(upstream, clienthello)
    )
    assert upstream().address == ("example.mitmproxy.org", 8081)
    assert upstream().sni == "example.mitmproxy.org"
    assert (
        proxy2
        >> DataReceived(tctx2.client, clienthello())
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(ClientTLSLayer)
        << TlsStartClientHook(Placeholder())
        >> reply_tls_start_client(alpn=b"http/1.1")
        << SendData(tctx2.client, serverhello)
    )
    assert (
        proxy1
        # forward serverhello to proxy1
        >> DataReceived(upstream, serverhello())
        << SendData(upstream, request)
    )
    assert (
        proxy2
        >> DataReceived(tctx2.client, request())
        << SendData(tctx2.client, tls_finished)
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.regular))
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        << SendData(tctx2.client, response)
    )
    assert server().address == ("example.com", 80)

    assert (
        proxy1
        >> DataReceived(upstream, tls_finished() + response())
        << SendData(tctx1.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )


@pytest.mark.parametrize("keep_host_header", [True, False])
def test_reverse_proxy(tctx, keep_host_header):
    """Test mitmproxy in reverse proxy mode.

    - make sure that we connect to the right host
    - make sure that we respect keep_host_header
    - make sure that we include non-standard ports in the host header (#4280)
    """
    server = Placeholder(Server)
    tctx.client.proxy_mode = ProxyMode.parse("reverse:http://localhost:8000")
    tctx.options.connection_strategy = "lazy"
    tctx.options.keep_host_header = keep_host_header
    assert (
        Playbook(modes.ReverseProxy(tctx), hooks=False)
        >> DataReceived(
            tctx.client, b"GET /foo HTTP/1.1\r\n" b"Host: example.com\r\n\r\n"
        )
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(lambda ctx: http.HttpLayer(ctx, HTTPMode.transparent))
        << OpenConnection(server)
        >> reply(None)
        << SendData(
            server,
            b"GET /foo HTTP/1.1\r\n"
            b"Host: "
            + (b"example.com" if keep_host_header else b"localhost:8000")
            + b"\r\n\r\n",
        )
        >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
        << SendData(tctx.client, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    )
    assert server().address == ("localhost", 8000)


def test_reverse_dns(tctx):
    tctx.client.transport_protocol = "udp"
    tctx.server.transport_protocol = "udp"

    f = Placeholder(dns.DNSFlow)
    server = Placeholder(Server)
    tctx.client.proxy_mode = ProxyMode.parse("reverse:dns://8.8.8.8:53")
    tctx.options.connection_strategy = "lazy"
    assert (
        Playbook(modes.ReverseProxy(tctx), hooks=False)
        >> DataReceived(tctx.client, tflow.tdnsreq().packed)
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(layers.DNSLayer)
        << layers.dns.DnsRequestHook(f)
        >> reply(None)
        << OpenConnection(server)
        >> reply(None)
        << SendData(tctx.server, tflow.tdnsreq().packed)
    )
    assert server().address == ("8.8.8.8", 53)


@pytest.mark.parametrize("keep_host_header", [True, False])
def test_quic(tctx: Context, keep_host_header: bool):
    with taddons.context():
        tctx.options.keep_host_header = keep_host_header
        tctx.server.sni = "other.example.com"
        tctx.client.proxy_mode = ProxyMode.parse("reverse:quic://example.org:443")
        client_hello = Placeholder(bytes)

        def set_settings(data: quic.QuicTlsData):
            data.settings = quic.QuicTlsSettings()

        assert (
            Playbook(modes.ReverseProxy(tctx))
            << OpenConnection(tctx.server)
            >> reply(None)
            >> DataReceived(tctx.client, b"\x00")
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(layers.ServerQuicLayer)
            << quic.QuicStartServerHook(Placeholder(quic.QuicTlsData))
            >> reply(side_effect=set_settings)
            << SendData(tctx.server, client_hello)
            << RequestWakeup(Placeholder(float))
        )
        assert tctx.server.address == ("example.org", 443)
        assert quic.quic_parse_client_hello_from_datagrams([client_hello()]).sni == (
            "other.example.com" if keep_host_header else "example.org"
        )


def test_udp(tctx: Context):
    tctx.client.proxy_mode = ProxyMode.parse("reverse:udp://1.2.3.4:5")
    flow = Placeholder(UDPFlow)
    assert (
        Playbook(modes.ReverseProxy(tctx))
        << OpenConnection(tctx.server)
        >> reply(None)
        >> DataReceived(tctx.client, b"test-input")
        << NextLayerHook(Placeholder(NextLayer))
        >> reply_next_layer(layers.UDPLayer)
        << udp.UdpStartHook(flow)
        >> reply()
        << udp.UdpMessageHook(flow)
        >> reply()
        << SendData(tctx.server, b"test-input")
    )
    assert tctx.server.address == ("1.2.3.4", 5)
    assert len(flow().messages) == 1
    assert flow().messages[0].content == b"test-input"


@pytest.mark.parametrize("patch", [True, False])
@pytest.mark.parametrize("connection_strategy", ["eager", "lazy"])
def test_reverse_proxy_tcp_over_tls(
    tctx: Context, monkeypatch, patch, connection_strategy
):
    """
    Test
        client --TCP-- mitmproxy --TCP over TLS-- server
    reverse proxying.
    """

    flow = Placeholder(TCPFlow)
    data = Placeholder(bytes)
    tctx.client.proxy_mode = ProxyMode.parse("reverse:https://localhost:8000")
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
        (playbook >> DataReceived(tctx.client, b"\x01\x02\x03"))
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
                # only now we open a connection
                << OpenConnection(tctx.server)
                >> reply(None)
            )
        assert (
            playbook << TcpMessageHook(flow) >> reply() << SendData(tctx.server, data)
        )
        assert data() == b"\x01\x02\x03"
    else:
        (
            playbook
            << NextLayerHook(Placeholder(NextLayer))
            >> reply_next_layer(tls.ServerTLSLayer)
        )
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
            << TlsStartServerHook(Placeholder())
            >> reply_tls_start_server()
            << SendData(tctx.server, data)
        )
        assert tls.parse_client_hello(data()).sni == "localhost"


@pytest.mark.parametrize("connection_strategy", ["eager", "lazy"])
def test_transparent_tcp(tctx: Context, connection_strategy):
    flow = Placeholder(TCPFlow)
    tctx.options.connection_strategy = connection_strategy
    tctx.server.address = ("address", 22)

    playbook = Playbook(modes.TransparentProxy(tctx))
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


def test_reverse_eager_connect_failure(tctx: Context):
    """
    Test
        client --TCP-- mitmproxy --TCP over TLS-- server
    reverse proxying.
    """

    tctx.client.proxy_mode = ProxyMode.parse("reverse:https://localhost:8000")
    tctx.options.connection_strategy = "eager"
    playbook = Playbook(modes.ReverseProxy(tctx))
    assert (
        playbook
        << OpenConnection(tctx.server)
        >> reply("IPoAC unstable")
        << CloseConnection(tctx.client)
        >> ConnectionClosed(tctx.client)
    )


def test_transparent_eager_connect_failure(tctx: Context):
    """Test that we recover from a transparent mode connect error."""
    tctx.options.connection_strategy = "eager"
    tctx.server.address = ("address", 22)

    assert (
        Playbook(modes.TransparentProxy(tctx), logs=True)
        << OpenConnection(tctx.server)
        >> reply("something something")
        << CloseConnection(tctx.client)
        >> ConnectionClosed(tctx.client)
    )


CLIENT_HELLO = b"\x05\x01\x00"
SERVER_HELLO = b"\x05\x00"


@pytest.mark.parametrize(
    "address,packed",
    [
        ("127.0.0.1", b"\x01\x7f\x00\x00\x01"),
        (
            "::1",
            b"\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
        ),
        ("example.com", b"\x03\x0bexample.com"),
    ],
)
def test_socks5_success(address: str, packed: bytes, tctx: Context):
    tctx.options.connection_strategy = "eager"
    playbook = Playbook(modes.Socks5Proxy(tctx))
    server = Placeholder(Server)
    nextlayer = Placeholder(NextLayer)
    assert (
        playbook
        >> DataReceived(tctx.client, CLIENT_HELLO)
        << SendData(tctx.client, SERVER_HELLO)
        >> DataReceived(
            tctx.client, b"\x05\x01\x00" + packed + b"\x12\x34applicationdata"
        )
        << OpenConnection(server)
        >> reply(None)
        << SendData(tctx.client, b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        << NextLayerHook(nextlayer)
    )
    assert server().address == (address, 0x1234)
    assert nextlayer().data_client() == b"applicationdata"


def _valid_socks_auth(data: modes.Socks5AuthData):
    data.valid = True


def test_socks5_trickle(tctx: Context):
    ProxyAuth().load(tctx.options)
    tctx.options.proxyauth = "user:password"
    tctx.options.connection_strategy = "lazy"
    playbook = Playbook(modes.Socks5Proxy(tctx))
    for x in b"\x05\x01\x02":
        playbook >> DataReceived(tctx.client, bytes([x]))
    playbook << SendData(tctx.client, b"\x05\x02")
    for x in b"\x01\x04user\x08password":
        playbook >> DataReceived(tctx.client, bytes([x]))
    playbook << modes.Socks5AuthHook(Placeholder())
    playbook >> reply(side_effect=_valid_socks_auth)
    playbook << SendData(tctx.client, b"\x01\x00")
    for x in b"\x05\x01\x00\x01\x7f\x00\x00\x01\x12\x34":
        playbook >> DataReceived(tctx.client, bytes([x]))
    assert playbook << SendData(
        tctx.client, b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    )


@pytest.mark.parametrize(
    "data,err,msg",
    [
        (
            b"GET / HTTP/1.1",
            None,
            "Probably not a SOCKS request but a regular HTTP request. Invalid SOCKS version. Expected 0x05, got 0x47",
        ),
        (b"abcd", None, "Invalid SOCKS version. Expected 0x05, got 0x61"),
        (
            CLIENT_HELLO + b"\x05\x02\x00\x01\x7f\x00\x00\x01\x12\x34",
            SERVER_HELLO + b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00",
            r"Unsupported SOCKS5 request: b'\x05\x02\x00\x01\x7f\x00\x00\x01\x124'",
        ),
        (
            CLIENT_HELLO + b"\x05\x01\x00\xff\x00\x00",
            SERVER_HELLO + b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00",
            r"Unknown address type: 255",
        ),
    ],
)
def test_socks5_err(data: bytes, err: bytes, msg: str, tctx: Context):
    playbook = Playbook(modes.Socks5Proxy(tctx), logs=True) >> DataReceived(
        tctx.client, data
    )
    if err:
        playbook << SendData(tctx.client, err)
    playbook << CloseConnection(tctx.client)
    playbook << Log(msg)
    assert playbook


@pytest.mark.parametrize(
    "client_greeting,server_choice,client_auth,server_resp,address,packed",
    [
        (
            b"\x05\x01\x02",
            b"\x05\x02",
            b"\x01\x04user\x08password",
            b"\x01\x00",
            "127.0.0.1",
            b"\x01\x7f\x00\x00\x01",
        ),
        (
            b"\x05\x02\x01\x02",
            b"\x05\x02",
            b"\x01\x04user\x08password",
            b"\x01\x00",
            "127.0.0.1",
            b"\x01\x7f\x00\x00\x01",
        ),
    ],
)
def test_socks5_auth_success(
    client_greeting: bytes,
    server_choice: bytes,
    client_auth: bytes,
    server_resp: bytes,
    address: bytes,
    packed: bytes,
    tctx: Context,
):
    ProxyAuth().load(tctx.options)
    tctx.options.proxyauth = "user:password"
    server = Placeholder(Server)
    nextlayer = Placeholder(NextLayer)
    playbook = (
        Playbook(modes.Socks5Proxy(tctx), logs=True)
        >> DataReceived(tctx.client, client_greeting)
        << SendData(tctx.client, server_choice)
        >> DataReceived(tctx.client, client_auth)
        << modes.Socks5AuthHook(Placeholder(modes.Socks5AuthData))
        >> reply(side_effect=_valid_socks_auth)
        << SendData(tctx.client, server_resp)
        >> DataReceived(
            tctx.client, b"\x05\x01\x00" + packed + b"\x12\x34applicationdata"
        )
        << OpenConnection(server)
        >> reply(None)
        << SendData(tctx.client, b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        << NextLayerHook(nextlayer)
    )
    assert playbook
    assert server().address == (address, 0x1234)
    assert nextlayer().data_client() == b"applicationdata"


@pytest.mark.parametrize(
    "client_greeting,server_choice,client_auth,err,msg",
    [
        (
            b"\x05\x01\x00",
            None,
            None,
            b"\x05\xff\x00\x01\x00\x00\x00\x00\x00\x00",
            "Client does not support SOCKS5 with user/password authentication.",
        ),
        (
            b"\x05\x02\x00\x02",
            b"\x05\x02",
            b"\x01\x04" + b"user" + b"\x07" + b"errcode",
            b"\x01\x01",
            "authentication failed",
        ),
    ],
)
def test_socks5_auth_fail(
    client_greeting: bytes,
    server_choice: bytes,
    client_auth: bytes,
    err: bytes,
    msg: str,
    tctx: Context,
):
    ProxyAuth().load(tctx.options)
    tctx.options.proxyauth = "user:password"
    playbook = Playbook(modes.Socks5Proxy(tctx), logs=True) >> DataReceived(
        tctx.client, client_greeting
    )
    if server_choice is None:
        playbook << SendData(tctx.client, err)
    else:
        playbook << SendData(tctx.client, server_choice)
        playbook >> DataReceived(tctx.client, client_auth)
        playbook << modes.Socks5AuthHook(Placeholder(modes.Socks5AuthData))
        playbook >> reply()
        playbook << SendData(tctx.client, err)

    playbook << CloseConnection(tctx.client)
    playbook << Log(msg)
    assert playbook


def test_socks5_eager_err(tctx: Context):
    tctx.options.connection_strategy = "eager"
    server = Placeholder(Server)
    assert (
        Playbook(modes.Socks5Proxy(tctx))
        >> DataReceived(tctx.client, CLIENT_HELLO)
        << SendData(tctx.client, SERVER_HELLO)
        >> DataReceived(tctx.client, b"\x05\x01\x00\x01\x7f\x00\x00\x01\x12\x34")
        << OpenConnection(server)
        >> reply("out of socks")
        << SendData(tctx.client, b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
        << CloseConnection(tctx.client)
    )


def test_socks5_premature_close(tctx: Context):
    assert (
        Playbook(modes.Socks5Proxy(tctx), logs=True)
        >> DataReceived(tctx.client, b"\x05")
        >> ConnectionClosed(tctx.client)
        << Log(r"Client closed connection before completing SOCKS5 handshake: b'\x05'")
        << CloseConnection(tctx.client)
    )
