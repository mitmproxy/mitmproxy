import pytest

from mitmproxy.proxy.commands import CloseConnection, OpenConnection, SendData
from mitmproxy.proxy.events import ConnectionClosed, DataReceived
from mitmproxy.proxy.layers import tcp
from mitmproxy.proxy.layers.tcp import TcpMessageInjected
from mitmproxy.tcp import TCPFlow, TCPMessage
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

    tctx.server.timestamp_start = 1624544785
    assert (
            Playbook(tcp.TCPLayer(tctx, True))
            << None
    )


def test_open_connection_err(tctx):
    f = Placeholder(TCPFlow)
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
    f = Placeholder(TCPFlow)

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
            << CloseConnection(tctx.client, half_close=True)
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
            >> DataReceived(tctx.client, b"eof-delimited-request")
            << SendData(tctx.server, b"eof-delimited-request")
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.server, half_close=True)
            >> DataReceived(tctx.server, b"i'm late")
            << SendData(tctx.client, b"i'm late")
            >> ConnectionClosed(tctx.server)
            << CloseConnection(tctx.client)
    )


@pytest.mark.parametrize("ignore", [True, False])
def test_ignore(tctx, ignore):
    """
    no flow hooks when we set ignore.
    """

    def no_flow_hooks():
        assert (
                Playbook(tcp.TCPLayer(tctx, ignore=ignore), hooks=True)
                << OpenConnection(tctx.server)
                >> reply(None)
                >> DataReceived(tctx.client, b"hello!")
                << SendData(tctx.server, b"hello!")
        )

    if ignore:
        no_flow_hooks()
    else:
        with pytest.raises(AssertionError):
            no_flow_hooks()


def test_inject(tctx):
    """inject data into an open connection."""
    f = Placeholder(TCPFlow)

    assert (
            Playbook(tcp.TCPLayer(tctx))
            << tcp.TcpStartHook(f)
            >> TcpMessageInjected(f, TCPMessage(True, b"hello!"))
            >> reply(to=-2)
            << OpenConnection(tctx.server)
            >> reply(None)
            << tcp.TcpMessageHook(f)
            >> reply()
            << SendData(tctx.server, b"hello!")
            # and the other way...
            >> TcpMessageInjected(f, TCPMessage(False, b"I have already done the greeting for you."))
            << tcp.TcpMessageHook(f)
            >> reply()
            << SendData(tctx.client, b"I have already done the greeting for you.")
            << None
    )
    assert len(f().messages) == 2
