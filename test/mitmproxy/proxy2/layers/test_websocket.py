import secrets
from dataclasses import dataclass

import pytest

import wsproto
import wsproto.events
from mitmproxy.http import HTTPFlow
from mitmproxy.net.http import Request, Response
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2.commands import SendData, CloseConnection, Log
from mitmproxy.proxy2.context import Server, ConnectionState
from mitmproxy.proxy2.events import DataReceived, ConnectionClosed
from mitmproxy.proxy2.layers import http, websocket
from mitmproxy.websocket import WebSocketFlow
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply


@dataclass
class _Masked:
    unmasked: bytes

    def __eq__(self, other):
        other = bytearray(other)
        assert other[1] & 0b1000_0000  # assert this is actually masked
        other[1] &= 0b0111_1111  # remove mask bit
        assert other[1] < 126  # (we don't support extended payload length here)
        mask = other[2:6]
        payload = bytes([x ^ mask[i % 4] for i, x in enumerate(other[6:])])
        return self.unmasked == other[:2] + payload


# noinspection PyTypeChecker
def masked(unmasked: bytes) -> bytes:
    return _Masked(unmasked)  # type: ignore


def masked_bytes(unmasked: bytes) -> bytes:
    header = bytearray(unmasked[:2])
    assert header[1] < 126  # assert that this is neither masked nor extended payload
    header[1] |= 0b1000_0000
    mask = secrets.token_bytes(4)
    masked = bytes([x ^ mask[i % 4] for i, x in enumerate(unmasked[2:])])
    return bytes(header + mask + masked)


def test_masking():
    m = masked(b"\x02\x03foo")
    assert m == b"\x02\x83\x1c\x96\xd4\rz\xf9\xbb"
    assert m == masked_bytes(b"\x02\x03foo")


def test_upgrade(tctx):
    """Test a HTTP -> WebSocket upgrade"""
    tctx.server.address = ("example.com", 80)
    tctx.server.state = ConnectionState.OPEN
    http_flow = Placeholder(HTTPFlow)
    flow = Placeholder(WebSocketFlow)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent))
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
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.client, masked_bytes(b"\x81\x0bhello world"))
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.server, masked(b"\x81\x0bhello world"))
            >> DataReceived(tctx.server, b"\x82\nhello back")
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.client, b"\x82\nhello back")
    )
    assert flow().handshake_flow == http_flow()
    assert len(flow().messages) == 2
    assert flow().messages[0].content == "hello world"
    assert flow().messages[0].from_client
    assert flow().messages[1].content == b"hello back"
    assert flow().messages[1].from_client is False


@pytest.fixture()
def ws_testdata(tctx):
    tctx.server.address = ("example.com", 80)
    tctx.server.state = ConnectionState.OPEN
    flow = HTTPFlow(
        tctx.client,
        tctx.server
    )
    flow.request = Request.make("GET", "http://example.com/", headers={
        "Connection": "upgrade",
        "Upgrade": "websocket",
        "Sec-WebSocket-Version": "13",
    })
    flow.response = Response.make(101, headers={
        "Connection": "upgrade",
        "Upgrade": "websocket",
    })
    return tctx, Playbook(websocket.WebsocketLayer(tctx, flow))


def test_modify_message(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x03foo")
            << websocket.WebsocketMessageHook(flow)
    )
    flow().messages[-1].content = flow().messages[-1].content.replace("foo", "foobar")
    assert (
            playbook
            >> reply()
            << SendData(tctx.client, b"\x81\x06foobar")
    )


def test_drop_message(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x03foo")
            << websocket.WebsocketMessageHook(flow)
    )
    flow().messages[-1].content = ""
    assert (
            playbook
            >> reply()
            << None
    )


def test_fragmented(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x01\x03foo")
            >> DataReceived(tctx.server, b"\x80\x03bar")
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.client, b"\x01\x03foo")
            << SendData(tctx.client, b"\x80\x03bar")
    )
    assert flow().messages[-1].content == "foobar"


def test_protocol_error(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x01\x03foo")
            >> DataReceived(tctx.server, b"\x02\x03bar")
            << SendData(tctx.server, masked(b"\x88/\x03\xeaexpected CONTINUATION, got <Opcode.BINARY: 2>"))
            << CloseConnection(tctx.server)
            << SendData(tctx.client, b"\x88/\x03\xeaexpected CONTINUATION, got <Opcode.BINARY: 2>")
            << CloseConnection(tctx.client)
            << websocket.WebsocketErrorHook(flow)
            >> reply()

    )
    assert not flow().messages


def test_ping(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.client, masked_bytes(b"\x89\x11ping-with-payload"))
            << Log("Received WebSocket ping from client (payload: b'ping-with-payload')")
            << SendData(tctx.server, masked(b"\x89\x11ping-with-payload"))
            >> DataReceived(tctx.server, b"\x8a\x11pong-with-payload")
            << Log("Received WebSocket pong from server (payload: b'pong-with-payload')")
            << SendData(tctx.client, b"\x8a\x11pong-with-payload")
    )
    assert not flow().messages


def test_close_normal(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    masked_close = Placeholder(bytes)
    close = Placeholder(bytes)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.client, masked_bytes(b"\x88\x00"))
            << SendData(tctx.server, masked_close)
            << CloseConnection(tctx.server)
            << SendData(tctx.client, close)
            << CloseConnection(tctx.client)
            << websocket.WebsocketEndHook(flow)
            >> reply()
    )
    # wsproto currently handles this inconsistently, see
    # https://github.com/python-hyper/wsproto/pull/153/files
    assert masked_close() == masked(b"\x88\x02\x03\xe8") or masked_close() == masked(b"\x88\x00")
    assert close() == b"\x88\x02\x03\xe8" or close() == b"\x88\x00"

    assert flow().close_code == 1005


def test_close_disconnect(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.server)
            << SendData(tctx.client, b"\x88\x02\x03\xe8")
            << CloseConnection(tctx.client)
            << websocket.WebsocketErrorHook(flow)
            >> reply()
            >> ConnectionClosed(tctx.client)
    )
    assert "ABNORMAL_CLOSURE" in flow().error.msg


def test_close_error(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x88\x02\x0f\xa0")
            << SendData(tctx.server, masked(b"\x88\x02\x0f\xa0"))
            << CloseConnection(tctx.server)
            << SendData(tctx.client, b"\x88\x02\x0f\xa0")
            << CloseConnection(tctx.client)
            << websocket.WebsocketErrorHook(flow)
            >> reply()
    )
    assert "UNKNOWN_ERROR=4000" in flow().error.msg


def test_deflate(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    # noinspection PyUnresolvedReferences
    http_flow: HTTPFlow = playbook.layer.flow.handshake_flow
    http_flow.response.headers["Sec-WebSocket-Extensions"] = "permessage-deflate; server_max_window_bits=10"
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            # https://tools.ietf.org/html/rfc7692#section-7.2.3.1
            >> DataReceived(tctx.server, bytes.fromhex("c1 07 f2 48 cd c9 c9 07 00"))
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.client, bytes.fromhex("c1 07 f2 48 cd c9 c9 07 00"))
    )
    assert flow().messages[0].content == "Hello"


def test_unknown_ext(ws_testdata):
    tctx, playbook = ws_testdata
    flow = Placeholder(WebSocketFlow)
    # noinspection PyUnresolvedReferences
    http_flow: HTTPFlow = playbook.layer.flow.handshake_flow
    http_flow.response.headers["Sec-WebSocket-Extensions"] = "funky-bits; param=42"
    assert (
            playbook
            << Log("Ignoring unknown WebSocket extension 'funky-bits'.")
            << websocket.WebsocketStartHook(flow)
            >> reply()
    )


def test_websocket_connection_repr(tctx):
    ws = websocket.WebsocketConnection(wsproto.ConnectionType.SERVER, conn=tctx.client)
    assert repr(ws)


class TestFragmentizer:
    def test_empty(self):
        f = websocket.Fragmentizer([b"foo"])
        assert list(f(b"")) == []

    def test_keep_sizes(self):
        f = websocket.Fragmentizer([b"foo", b"bar"])
        assert list(f(b"foobaz")) == [
            wsproto.events.Message(b"foo", message_finished=False),
            wsproto.events.Message(b"baz", message_finished=True),
        ]

    def test_rechunk(self):
        f = websocket.Fragmentizer([b"foo"])
        f.FRAGMENT_SIZE = 4
        assert list(f(b"foobar")) == [
            wsproto.events.Message(b"foob", message_finished=False),
            wsproto.events.Message(b"ar", message_finished=True),
        ]
