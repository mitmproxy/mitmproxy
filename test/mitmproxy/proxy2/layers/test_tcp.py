from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.layers import tcp
from .. import tutils


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


def test_open_connection_err(tctx):
    f = tutils.Placeholder()
    assert (
        tutils.playbook(tcp.TCPLayer(tctx))
        << commands.Hook("tcp_start", f)
        >> events.HookReply(-1, None)
        << commands.OpenConnection(tctx.server)
        >> events.OpenConnectionReply(-1, "Connect call failed")
        << commands.Hook("tcp_error", f)
        >> events.HookReply(-1, None)
        << commands.CloseConnection(tctx.client)
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
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.server, b"hello!")
        >> events.DataReceived(tctx.server, b"hi")
        << commands.Hook("tcp_message", f)
        >> events.HookReply(-1, None)
        << commands.SendData(tctx.client, b"hi")
        >> events.ConnectionClosed(tctx.server)
        << commands.CloseConnection(tctx.client)
        << commands.Hook("tcp_end", f)
        >> events.HookReply(-1, None)
        >> events.ConnectionClosed(tctx.client)
        << None
    )
    assert len(f().messages) == 2


def test_simple_explicit(tctx):
    """
    For comparison, test_simple without the playbook() sugar.
    This is not substantially more code, but the playbook syntax feels cleaner to me.
    """
    layer = tcp.TCPLayer(tctx)
    tcp_start, = layer.handle_event(events.Start())
    flow = tcp_start.data
    assert tutils._eq(tcp_start, commands.Hook("tcp_start", flow))
    open_conn, = layer.handle_event(events.HookReply(tcp_start, None))
    assert tutils._eq(open_conn, commands.OpenConnection(tctx.server))
    assert list(layer.handle_event(events.OpenConnectionReply(open_conn, None))) == []
    tcp_msg, = layer.handle_event(events.DataReceived(tctx.client, b"hello!"))
    assert tutils._eq(tcp_msg, commands.Hook("tcp_message", flow))
    assert flow.messages[0].content == b"hello!"

    send, = layer.handle_event(events.HookReply(tcp_msg, None))
    assert tutils._eq(send, commands.SendData(tctx.server, b"hello!"))
    close, tcp_end = layer.handle_event(events.ConnectionClosed(tctx.server))
    assert tutils._eq(close, commands.CloseConnection(tctx.client))
    assert tutils._eq(tcp_end, commands.Hook("tcp_end", flow))
    assert list(layer.handle_event(events.HookReply(tcp_end, None))) == []


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
    assert f().messages


def test_receive_data_after_server_disconnected(tctx):
    """
    data received after a connection has been closed should just be discarded.
    """
    f = tutils.Placeholder()
    assert (
        tutils.playbook(tcp.TCPLayer(tctx))
        << commands.Hook("tcp_start", f)
        >> events.HookReply(-1, None)
        << commands.OpenConnection(tctx.server)
        >> events.OpenConnectionReply(-1, None)
        >> events.ConnectionClosed(tctx.server)
        << commands.CloseConnection(tctx.client)
        << commands.Hook("tcp_end", f)
        >> events.HookReply(-1, None)
        >> events.DataReceived(tctx.client, b"i'm late")
        << None
    )
    # not included here as it has not been sent to the server.
    assert not f().messages
