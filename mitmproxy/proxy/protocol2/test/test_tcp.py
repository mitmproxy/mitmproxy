from mitmproxy.proxy.protocol2 import tcp
from mitmproxy.proxy.protocol2.test.tutils import playbook
from .. import commands
from .. import events


def test_open_connection(tctx):
    """
    If there is no server connection yet, establish one,
    because the server may send data first.
    """
    assert (
        playbook(tcp.TCPLayer(tctx))
        << commands.OpenConnection(tctx.server)
    )

    tctx.server.connected = True
    assert (
        playbook(tcp.TCPLayer(tctx))
        << None
    )


def test_simple(tctx):
    """open connection, receive data, send it to peer"""
    assert (
        playbook(tcp.TCPLayer(tctx))
        << commands.OpenConnection(tctx.server)
        >> events.OpenConnectionReply(-1, "ok")
        >> events.ClientDataReceived(tctx.client, b"hello!")
        << commands.SendData(tctx.server, b"hello!")
    )


def test_receive_data_before_server_connected(tctx):
    """
    assert that data received before a server connection is established
    will still be forwarded.
    """
    assert (
        playbook(tcp.TCPLayer(tctx))
        << commands.OpenConnection(tctx.server)
        >> events.ClientDataReceived(tctx.client, b"hello!")
        >> events.OpenConnectionReply(-2, "ok")
        << commands.SendData(tctx.server, b"hello!")
    )
