import secrets
from dataclasses import dataclass

import pytest

import wsproto
import wsproto.events
from mitmproxy.http import HTTPFlow, Request, Response
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.commands import SendData, CloseConnection, Log
from mitmproxy.connection import ConnectionState
from mitmproxy.proxy.events import DataReceived, ConnectionClosed
from mitmproxy.proxy.layers import http, websocket
from mitmproxy.proxy.layers.websocket import WebSocketMessageInjected
from mitmproxy.websocket import WebSocketData, WebSocketMessage
from test.mitmproxy.proxy.tutils import Placeholder, Playbook, reply
from wsproto.frame_protocol import Opcode


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
    flow = Placeholder(HTTPFlow)
    assert (
            Playbook(http.HttpLayer(tctx, HTTPMode.transparent))
            >> DataReceived(tctx.client,
                            b"GET / HTTP/1.1\r\n"
                            b"Connection: upgrade\r\n"
                            b"Upgrade: websocket\r\n"
                            b"Sec-WebSocket-Version: 13\r\n"
                            b"\r\n")
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
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
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
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
            >> DataReceived(tctx.client, masked_bytes(b"\x81\x0bhello again"))
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.server, masked(b"\x81\x0bhello again"))
    )
    assert len(flow().websocket.messages) == 3
    assert flow().websocket.messages[0].content == b"hello world"
    assert flow().websocket.messages[0].from_client
    assert flow().websocket.messages[0].type == Opcode.TEXT
    assert flow().websocket.messages[1].content == b"hello back"
    assert flow().websocket.messages[1].from_client is False
    assert flow().websocket.messages[1].type == Opcode.BINARY


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
    flow.websocket = WebSocketData()
    return tctx, Playbook(websocket.WebsocketLayer(tctx, flow)), flow


def test_modify_message(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x03foo")
            << websocket.WebsocketMessageHook(flow)
    )
    flow.websocket.messages[-1].content = flow.websocket.messages[-1].content.replace(b"foo", b"foobar")
    assert (
            playbook
            >> reply()
            << SendData(tctx.client, b"\x81\x06foobar")
    )


def test_empty_message(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x00")
            << websocket.WebsocketMessageHook(flow)
    )
    assert flow.websocket.messages[-1].content == b""
    assert (
            playbook
            >> reply()
            << SendData(tctx.client, b"\x81\x00")
    )


def test_drop_message(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x03foo")
            << websocket.WebsocketMessageHook(flow)
    )
    flow.websocket.messages[-1].drop()
    assert (
            playbook
            >> reply()
            << None
    )


def test_fragmented(ws_testdata):
    tctx, playbook, flow = ws_testdata
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
    assert flow.websocket.messages[-1].content == b"foobar"


def test_unfragmented(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x81\x06foo")
    )
    # This already triggers wsproto to emit a wsproto.events.Message, see
    # https://github.com/mitmproxy/mitmproxy/issues/4701
    assert(
            playbook
            >> DataReceived(tctx.server, b"bar")
            << websocket.WebsocketMessageHook(flow)
            >> reply()
            << SendData(tctx.client, b"\x81\x06foobar")
    )
    assert flow.websocket.messages[-1].content == b"foobar"


def test_protocol_error(ws_testdata):
    tctx, playbook, flow = ws_testdata
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
            << websocket.WebsocketEndHook(flow)
            >> reply()

    )
    assert not flow.websocket.messages


def test_ping(ws_testdata):
    tctx, playbook, flow = ws_testdata
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
    assert not flow.websocket.messages


def test_close_normal(ws_testdata):
    tctx, playbook, flow = ws_testdata
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

    assert flow.websocket.close_code == 1005


def test_close_disconnect(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.server)
            << SendData(tctx.client, b"\x88\x02\x03\xe8")
            << CloseConnection(tctx.client)
            << websocket.WebsocketEndHook(flow)
            >> reply()
            >> ConnectionClosed(tctx.client)
    )
    # The \x03\xe8 above is code 1000 (normal closure).
    # But 1006 (ABNORMAL_CLOSURE) is expected, because the connection was already closed.
    assert flow.websocket.close_code == 1006


def test_close_code(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> DataReceived(tctx.server, b"\x88\x02\x0f\xa0")
            << SendData(tctx.server, masked(b"\x88\x02\x0f\xa0"))
            << CloseConnection(tctx.server)
            << SendData(tctx.client, b"\x88\x02\x0f\xa0")
            << CloseConnection(tctx.client)
            << websocket.WebsocketEndHook(flow)
            >> reply()
    )
    assert flow.websocket.close_code == 4000


def test_deflate(ws_testdata):
    tctx, playbook, flow = ws_testdata
    flow.response.headers["Sec-WebSocket-Extensions"] = "permessage-deflate; server_max_window_bits=10"
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
    assert flow.websocket.messages[0].content == b"Hello"


def test_unknown_ext(ws_testdata):
    tctx, playbook, flow = ws_testdata
    flow.response.headers["Sec-WebSocket-Extensions"] = "funky-bits; param=42"
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
        f = websocket.Fragmentizer([b"foo"], False)
        assert list(f(b"")) == [
            wsproto.events.BytesMessage(b"", message_finished=True),
        ]

    def test_keep_sizes(self):
        f = websocket.Fragmentizer([b"foo", b"bar"], True)
        assert list(f(b"foobaz")) == [
            wsproto.events.TextMessage("foo", message_finished=False),
            wsproto.events.TextMessage("baz", message_finished=True),
        ]

    def test_rechunk(self):
        f = websocket.Fragmentizer([b"foo"], False)
        f.FRAGMENT_SIZE = 4
        assert list(f(b"foobar")) == [
            wsproto.events.BytesMessage(b"foob", message_finished=False),
            wsproto.events.BytesMessage(b"ar", message_finished=True),
        ]


def test_inject_message(ws_testdata):
    tctx, playbook, flow = ws_testdata
    assert (
            playbook
            << websocket.WebsocketStartHook(flow)
            >> reply()
            >> WebSocketMessageInjected(flow, WebSocketMessage(Opcode.TEXT, False, b"hello"))
            << websocket.WebsocketMessageHook(flow)
    )
    assert flow.websocket.messages[-1].content == b"hello"
    assert flow.websocket.messages[-1].from_client is False
    assert (
            playbook
            >> reply()
            << SendData(tctx.client, b"\x81\x05hello")
    )
