from unittest import mock

import pytest

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
        )
    )
    with mock.patch("os.urandom") as m:
        m.return_value = b"\x10\x11\x12\x13"
        yield playbook


def test_simple(tctx, ws_playbook):
    f = tutils.Placeholder()

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.client, b"\x82\x85\x10\x11\x12\x13Xt~\x7f\x7f")  # Frame with payload b"Hello"
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.server, b"\x82\x85\x10\x11\x12\x13Xt~\x7f\x7f")
        >> events.DataReceived(tctx.server, b'\x81\x05Hello')  # Frame with payload "Hello"
        << commands.Hook("websocket_message", f)
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.client, b'\x81\x05Hello')
        >> events.DataReceived(tctx.client, b'\x88\x82\x10\x11\x12\x13\x13\xf9')  # Closing frame
        << commands.SendData(tctx.server, b'\x88\x82\x10\x11\x12\x13\x13\xf9')
        << commands.SendData(tctx.client, b'\x88\x02\x03\xe8')
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.server, b'\x81\x05Hello')
        << None
    )

    assert len(f().messages) == 2


def test_server_close(tctx, ws_playbook):
    f = tutils.Placeholder()

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.server, b'\x88\x02\x03\xe8')
        << commands.SendData(tctx.client, b'\x88\x02\x03\xe8')
        << commands.SendData(tctx.server, b'\x88\x82\x10\x11\x12\x13\x13\xf9')
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1, None)
        << commands.CloseConnection(tctx.client)
    )


def test_ping_pong(tctx, ws_playbook):
    f = tutils.Placeholder()

    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.client, b'\x89\x80\x10\x11\x12\x13')  # Ping
        << commands.Log("info", "Websocket PING received ")
        << commands.SendData(tctx.server, b'\x89\x80\x10\x11\x12\x13')
        << commands.SendData(tctx.client, b'\x8a\x00')
        >> events.DataReceived(tctx.server, b'\x8a\x00')  # Pong
        << commands.Log("info", "Websocket PONG received ")
    )


def test_connection_failed(tctx, ws_playbook):
    f = tutils.Placeholder()
    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.client, b"Not a valid frame")
        << commands.SendData(tctx.server, b'\x88\x94\x10\x11\x12\x13\x13\xfb[}fp~zt1}cs~vv0!jv')
        << commands.SendData(tctx.client, b'\x88\x14\x03\xeaInvalid opcode 0xe')
        << commands.Hook("websocket_error", f)
        >> events.HookReply(-1, None)
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1, None)
    )


def test_extension(tctx):
    f = tutils.Placeholder()
    tctx.server.connected = True
    handshake_flow = tflow.twebsocketflow().handshake_flow
    handshake_flow.request.headers["sec-websocket-extensions"] = "permessage-deflate;"
    handshake_flow.response.headers["sec-websocket-extensions"] = "permessage-deflate;"
    playbook = tutils.playbook(websocket.WebsocketLayer(tctx, handshake_flow))
    with mock.patch("os.urandom") as m:
        m.return_value = b"\x10\x11\x12\x13"
        assert (
            playbook
            << commands.Hook("websocket_start", f)
            >> events.HookReply(-1, None)
            >> events.DataReceived(tctx.client, b'\xc1\x87\x10\x11\x12\x13\xe2Y\xdf\xda\xd9\x16\x12')  # Compressed Frame
            << commands.Hook("websocket_message", f)
            >> events.HookReply(-1, None)
            << commands.SendData(tctx.server, b'\xc1\x87\x10\x11\x12\x13\xe2Y\xdf\xda\xd9\x16\x12')
            >> events.DataReceived(tctx.server, b'\xc1\x07\xf2H\xcd\xc9\xc9\x07\x00')  # Compressed Frame
            << commands.Hook("websocket_message", f)
            >> events.HookReply(-1, None)
            << commands.SendData(tctx.client, b'\xc1\x07\xf2H\xcd\xc9\xc9\x07\x00')
        )
    assert len(f().messages) == 2
    assert f().messages[0].content == "Hello"
    assert f().messages[1].content == "Hello"


def test_connection_closed(tctx, ws_playbook):
    f = tutils.Placeholder()
    assert (
        ws_playbook
        << commands.Hook("websocket_start", f)
        >> events.HookReply(-1, None)
        >> events.ConnectionClosed(tctx.server)
        << commands.Log("error", "Connection closed abnormally")
        << commands.CloseConnection(tctx.client)
        << commands.Hook("websocket_error", f)
        >> events.HookReply(-1, None)
        << commands.Hook("websocket_end", f)
        >> events.HookReply(-1, None)
    )

    assert f().error
