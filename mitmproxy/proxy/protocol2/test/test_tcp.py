from . import tutils
from .. import commands
from .. import events
from .. import tcp


def test_open_connection(tctx):
    """
    If there is no server connection yet, establish one,
    because the server may send data first.
    """
    assert (
        tutils.playbook(tcp.TCPLayer(tctx, True))
        << commands.OpenConnection(tctx.server)
    )

    tctx.server.connected = True
    assert (
        tutils.playbook(tcp.TCPLayer(tctx, True))
        << None
    )


def test_simple(tctx):
    """open connection, receive data, send it to peer"""
    f = tutils.Placeholder()
    playbook = tutils.playbook(tcp.TCPLayer(tctx))

    assert (
        playbook
        << commands.Hook("tcp_start", f)
        >> events.HookReply(-1, None)
        << commands.OpenConnection(tctx.server)
        >> events.OpenConnectionReply(-1, None)
        >> events.DataReceived(tctx.client, b"hello!")
        << commands.Hook("tcp_message", f)
    )
    assert f().messages[0].content == b"hello!"
    assert (
        playbook
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.server, b"hello!")
    )


def test_receive_data_before_server_connected(tctx):
    """
    assert that data received before a server connection is established
    will still be forwarded.
    """
    f = tutils.Placeholder()
    assert (
        tutils.playbook(tcp.TCPLayer(tctx))
        << commands.Hook("tcp_start", f)
        >> events.HookReply(-1, None)
        << commands.OpenConnection(tctx.server)
        >> events.DataReceived(tctx.client, b"hello!")
        >> events.OpenConnectionReply(-2, None)
        << commands.Hook("tcp_message", f)
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.server, b"hello!")
    )
