import struct
from unittest import mock

import pytest

from mitmproxy.net.websockets import Frame, OPCODE
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.layers import websocket
from mitmproxy.test import tflow
from .. import tutils


@pytest.fixture
def ws_playbook(tctx):
    tctx.server.connected = True
    playbook = tutils.playbook(
        websocket.WebsocketLayer(
            tctx,
            tflow.twebsocketflow().handshake_flow
        ),
        ignore_log=False,
    )
    with mock.patch("os.urandom") as m:
        m.return_value = b"\x10\x11\x12\x13"
        yield playbook


def test_simple(tctx, ws_playbook):
    f = tutils.Placeholder()

    frames = [
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.TEXT, payload=b'client-foobar')),
        bytes(Frame(fin=1, opcode=OPCODE.BINARY, payload=b'\xde\xad\xbe\xef')),
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1000))),
        bytes(Frame(fin=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1000))),
        bytes(Frame(fin=1, opcode=OPCODE.TEXT, payload=b'fail')),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.client, frames[0])
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1)
        << commands.SendData(tctx.server, frames[0])
        >> events.DataReceived(tctx.server, frames[1])
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1)
        << commands.SendData(tctx.client, frames[1])
        >> events.DataReceived(tctx.client, frames[2])
        << commands.SendData(tctx.server, frames[2])
        << commands.SendData(tctx.client, frames[3])
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.server, frames[4])
        << None
    )

    assert len(f().messages) == 2


def test_server_close(tctx, ws_playbook):
    f = tutils.Placeholder()

    frames = [
        bytes(Frame(fin=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1000))),
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1000))),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.server, frames[0])
        << commands.SendData(tctx.client, frames[0])
        << commands.SendData(tctx.server, frames[1])
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1)
        << commands.CloseConnection(tctx.client)
    )


def test_connection_closed(tctx, ws_playbook):
    f = tutils.Placeholder()
    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.ConnectionClosed(tctx.server)
        << commands.Log("error", "Connection closed abnormally")
        << commands.CloseConnection(tctx.client)
        << commands.Hook("websocket_error", f)
        >> events.HookReply(-1)
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1)
    )

    assert f().error


def test_connection_failed(tctx, ws_playbook):
    f = tutils.Placeholder()

    frames = [
        b'Not a valid frame',
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1002) + b'Invalid opcode 0xe')),
        bytes(Frame(fin=1, opcode=OPCODE.CLOSE, payload=struct.pack('>H', 1002) + b'Invalid opcode 0xe')),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.client, frames[0])
        << commands.SendData(tctx.server, frames[1])
        << commands.SendData(tctx.client, frames[2])
        << commands.Hook("websocket_error", f)
        >> events.HookReply(-1)
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1)
    )


def test_ping_pong(tctx, ws_playbook):
    f = tutils.Placeholder()

    frames = [
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.PING)),
        bytes(Frame(fin=1, opcode=OPCODE.PONG)),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.client, frames[0])
        << commands.Log("info", "WebSocket PING received from client: <no payload>")
        << commands.SendData(tctx.server, frames[0])
        << commands.SendData(tctx.client, frames[1])
        >> events.DataReceived(tctx.server, frames[1])
        << commands.Log("info", "WebSocket PONG received from server: <no payload>")
    )


def test_ping_pong_hidden_payload(tctx, ws_playbook):
    f = tutils.Placeholder()

    frames = [
        bytes(Frame(fin=1, opcode=OPCODE.PING, payload=b'foobar')),
        bytes(Frame(fin=1, opcode=OPCODE.PING, payload=b'')),
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.PONG, payload=b'foobar')),
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.PONG, payload=b'')),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.server, frames[0])
        << commands.Log("info", "WebSocket PING received from server: foobar")
        << commands.SendData(tctx.client, frames[1])
        << commands.SendData(tctx.server, frames[2])
        >> events.DataReceived(tctx.client, frames[3])
        << commands.Log("info", "WebSocket PONG received from client: <no payload>")
    )


def test_extension(tctx, ws_playbook):
    f = tutils.Placeholder()

    ws_playbook.layer.handshake_flow.request.headers["sec-websocket-extensions"] = "permessage-deflate;"
    ws_playbook.layer.handshake_flow.response.headers["sec-websocket-extensions"] = "permessage-deflate;"

    frames = [
        bytes(Frame(fin=1, mask=1, opcode=OPCODE.TEXT, rsv1=True, payload=b'\xf2\x48\xcd\xc9\xc9\x07\x00')),
        bytes(Frame(fin=1, opcode=OPCODE.TEXT, rsv1=True, payload=b'\xf2\x48\xcd\xc9\xc9\x07\x00')),
        bytes(Frame(fin=1, opcode=OPCODE.TEXT, rsv1=True, payload=b'\xf2\x00\x11\x00\x00')),
    ]

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1)
        >> events.DataReceived(tctx.client, frames[0])
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1)
        << commands.SendData(tctx.server, frames[0])
        >> events.DataReceived(tctx.server, frames[1])
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1)
        << commands.SendData(tctx.client, frames[2])
    )
    assert len(f().messages) == 2
    assert f().messages[0].content == "Hello"
    assert f().messages[1].content == "Hello"
