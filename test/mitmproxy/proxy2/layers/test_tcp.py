from mitmproxy.proxy2.commands import CloseConnection, OpenConnection, SendData
from mitmproxy.proxy2.events import ConnectionClosed, DataReceived
from mitmproxy.proxy2.layers import tcp
from ..tutils import Placeholder, Playbook, reply


def test_open_connection(tctx):
    """
    If there is no server connection yet, establish one,
    because the server may send data first.
    """
    assert (
            Playbook(tcp.TCPLayer(tctx, True))
            << OpenConnection(tctx.server)
    )

    tctx.server.connected = True
    assert (
            Playbook(tcp.TCPLayer(tctx, True))
            << None
    )


def test_open_connection_err(tctx):
    f = Placeholder()
    assert (
            Playbook(tcp.TCPLayer(tctx))
            << tcp.TcpStartHook(f)
            >> reply()
            << OpenConnection(tctx.server)
            >> reply("Connect call failed")
            << tcp.TcpErrorHook(f)
            >> reply()
            << CloseConnection(tctx.client)
    )


def test_simple(tctx):
    """open connection, receive data, send it to peer"""
    f = Placeholder()

    assert (
            Playbook(tcp.TCPLayer(tctx))
            << tcp.TcpStartHook(f)
            >> reply()
            << OpenConnection(tctx.server)
            >> reply(None)
            >> DataReceived(tctx.client, b"hello!")
            << tcp.TcpMessageHook(f)
            >> reply()
            << SendData(tctx.server, b"hello!")
            >> DataReceived(tctx.server, b"hi")
            << tcp.TcpMessageHook(f)
            >> reply()
            << SendData(tctx.client, b"hi")
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.client)
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.server)
            << tcp.TcpEndHook(f)
            >> reply()
            >> ConnectionClosed(tctx.client)
            << None
    )
    assert len(f().messages) == 2


def test_receive_data_before_server_connected(tctx):
    """
    assert that data received before a server connection is established
    will still be forwarded.
    """
    assert (
            Playbook(tcp.TCPLayer(tctx), hooks=False)
            << OpenConnection(tctx.server)
            >> DataReceived(tctx.client, b"hello!")
            >> reply(None, to=-2)
            << SendData(tctx.server, b"hello!")
    )


def test_receive_data_after_half_close(tctx):
    """
    data received after the other connection has been half-closed should still be forwarded.
    """
    assert (
            Playbook(tcp.TCPLayer(tctx), hooks=False)
            << OpenConnection(tctx.server)
            >> reply(None)
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.client)
            >> DataReceived(tctx.client, b"i'm late")
            << SendData(tctx.server, b"i'm late")
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.server)
    )
