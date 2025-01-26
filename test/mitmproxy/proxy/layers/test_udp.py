import pytest

from ..tutils import Placeholder
from ..tutils import Playbook
from ..tutils import reply
from mitmproxy.proxy.commands import CloseConnection
from mitmproxy.proxy.commands import OpenConnection
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.events import ConnectionClosed
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers import udp
from mitmproxy.proxy.layers.udp import UdpMessageInjected
from mitmproxy.udp import UDPFlow
from mitmproxy.udp import UDPMessage


def test_open_connection(tctx):
    """
    If there is no server connection yet, establish one,
    because the server may send data first.
    """
    assert Playbook(udp.UDPLayer(tctx, True)) << OpenConnection(tctx.server)

    tctx.server.timestamp_start = 1624544785
    assert Playbook(udp.UDPLayer(tctx, True)) << None


def test_open_connection_err(tctx):
    f = Placeholder(UDPFlow)
    assert (
        Playbook(udp.UDPLayer(tctx))
        << udp.UdpStartHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply("Connect call failed")
        << udp.UdpErrorHook(f)
        >> reply()
        << CloseConnection(tctx.client)
    )


def test_simple(tctx):
    """open connection, receive data, send it to peer"""
    f = Placeholder(UDPFlow)

    assert (
        Playbook(udp.UDPLayer(tctx))
        << udp.UdpStartHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        >> DataReceived(tctx.client, b"hello!")
        << udp.UdpMessageHook(f)
        >> reply()
        << SendData(tctx.server, b"hello!")
        >> DataReceived(tctx.server, b"hi")
        << udp.UdpMessageHook(f)
        >> reply()
        << SendData(tctx.client, b"hi")
        >> ConnectionClosed(tctx.server)
        << CloseConnection(tctx.client)
        << udp.UdpEndHook(f)
        >> reply()
        >> DataReceived(tctx.server, b"ignored")
        << None
    )
    assert len(f().messages) == 2


def test_receive_data_before_server_connected(tctx):
    """
    assert that data received before a server connection is established
    will still be forwarded.
    """
    assert (
        Playbook(udp.UDPLayer(tctx), hooks=False)
        << OpenConnection(tctx.server)
        >> DataReceived(tctx.client, b"hello!")
        >> reply(None, to=-2)
        << SendData(tctx.server, b"hello!")
    )


@pytest.mark.parametrize("ignore", [True, False])
def test_ignore(tctx, ignore):
    """
    no flow hooks when we set ignore.
    """

    def no_flow_hooks():
        assert (
            Playbook(udp.UDPLayer(tctx, ignore=ignore), hooks=True)
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
    f = Placeholder(UDPFlow)

    assert (
        Playbook(udp.UDPLayer(tctx))
        << udp.UdpStartHook(f)
        >> UdpMessageInjected(f, UDPMessage(True, b"hello!"))
        >> reply(to=-2)
        << OpenConnection(tctx.server)
        >> reply(None)
        << udp.UdpMessageHook(f)
        >> reply()
        << SendData(tctx.server, b"hello!")
        # and the other way...
        >> UdpMessageInjected(
            f, UDPMessage(False, b"I have already done the greeting for you.")
        )
        << udp.UdpMessageHook(f)
        >> reply()
        << SendData(tctx.client, b"I have already done the greeting for you.")
        << None
    )
    assert len(f().messages) == 2
