from typing import Tuple, Optional

import pytest

from mitmproxy.proxy import tunnel, layer
from mitmproxy.proxy.commands import SendData, Log, CloseConnection, OpenConnection
from mitmproxy.connection import Server, ConnectionState
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import Event, DataReceived, Start, ConnectionClosed
from test.mitmproxy.proxy.tutils import Playbook, reply


class TChildLayer(layer.Layer):
    child_layer: Optional[layer.Layer] = None

    def _handle_event(self, event: Event) -> layer.CommandGenerator[None]:
        if isinstance(event, Start):
            yield Log(f"Got start. Server state: {self.context.server.state.name}")
        elif isinstance(event, DataReceived) and event.data == b"client-hello":
            yield SendData(self.context.client, b"client-hello-reply")
        elif isinstance(event, DataReceived) and event.data == b"server-hello":
            yield SendData(self.context.server, b"server-hello-reply")
        elif isinstance(event, DataReceived) and event.data == b"open":
            err = yield OpenConnection(self.context.server)
            yield Log(f"Opened: {err=}. Server state: {self.context.server.state.name}")
        elif isinstance(event, DataReceived) and event.data == b"half-close":
            err = yield CloseConnection(event.connection, half_close=True)
        elif isinstance(event, ConnectionClosed):
            yield Log(f"Got {event.connection.__class__.__name__.lower()} close.")
            yield CloseConnection(event.connection)
        else:
            raise AssertionError


class TTunnelLayer(tunnel.TunnelLayer):
    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield SendData(self.tunnel_connection, b"handshake-hello")

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        yield SendData(self.tunnel_connection, data)
        if data == b"handshake-success":
            return True, None
        else:
            return False, "handshake error"

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield SendData(self.tunnel_connection, b"tunneled-" + data)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(
            DataReceived(self.conn, data.replace(b"tunneled-", b""))
        )


@pytest.mark.parametrize("success", ["success", "fail"])
def test_tunnel_handshake_start(tctx: Context, success):
    server = Server(("proxy", 1234))
    server.state = ConnectionState.OPEN

    tl = TTunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)
    assert repr(tl)

    playbook = Playbook(tl, logs=True)
    (
            playbook
            << SendData(server, b"handshake-hello")
            >> DataReceived(tctx.client, b"client-hello")
            >> DataReceived(server, b"handshake-" + success.encode())
            << SendData(server, b"handshake-" + success.encode())
    )
    if success == "success":
        playbook << Log("Got start. Server state: OPEN")
    else:
        playbook << CloseConnection(server)
        playbook << Log("Got start. Server state: CLOSED")

    playbook << SendData(tctx.client, b"client-hello-reply")
    if success == "success":
        playbook >> DataReceived(server, b"tunneled-server-hello")
        playbook << SendData(server, b"tunneled-server-hello-reply")

    assert playbook


@pytest.mark.parametrize("success", ["success", "fail"])
def test_tunnel_handshake_command(tctx: Context, success):
    server = Server(("proxy", 1234))

    tl = TTunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)

    playbook = Playbook(tl, logs=True)
    (
            playbook
            << Log("Got start. Server state: CLOSED")
            >> DataReceived(tctx.client, b"client-hello")
            << SendData(tctx.client, b"client-hello-reply")
            >> DataReceived(tctx.client, b"open")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"handshake-hello")
            >> DataReceived(server, b"handshake-" + success.encode())
            << SendData(server, b"handshake-" + success.encode())
    )
    if success == "success":
        assert (
                playbook
                << Log(f"Opened: err=None. Server state: OPEN")
                >> DataReceived(server, b"tunneled-server-hello")
                << SendData(server, b"tunneled-server-hello-reply")
                >> ConnectionClosed(tctx.client)
                << Log("Got client close.")
                << CloseConnection(tctx.client)
        )
        assert tl.tunnel_state is tunnel.TunnelState.OPEN
        assert (
                playbook
                >> ConnectionClosed(server)
                << Log("Got server close.")
                << CloseConnection(server)
        )
        assert tl.tunnel_state is tunnel.TunnelState.CLOSED
    else:
        assert (
                playbook
                << CloseConnection(server)
                << Log("Opened: err='handshake error'. Server state: CLOSED")
        )
        assert tl.tunnel_state is tunnel.TunnelState.CLOSED


def test_tunnel_default_impls(tctx: Context):
    """
    Some tunnels don't need certain features, so the default behaviour
    should be to be transparent.
    """
    server = Server(None)
    server.state = ConnectionState.OPEN
    tl = tunnel.TunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)
    playbook = Playbook(tl, logs=True)
    assert (
            playbook
            << Log("Got start. Server state: OPEN")
            >> DataReceived(server, b"server-hello")
            << SendData(server, b"server-hello-reply")
    )
    assert tl.tunnel_state is tunnel.TunnelState.OPEN
    assert (
            playbook
            >> ConnectionClosed(server)
            << Log("Got server close.")
            << CloseConnection(server)
    )
    assert tl.tunnel_state is tunnel.TunnelState.CLOSED

    assert (
            playbook
            >> DataReceived(tctx.client, b"open")
            << OpenConnection(server)
            >> reply(None)
            << Log("Opened: err=None. Server state: OPEN")
            >> DataReceived(server, b"half-close")
            << CloseConnection(server, half_close=True)
    )


def test_tunnel_openconnection_error(tctx: Context):
    server = Server(("proxy", 1234))

    tl = TTunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)

    playbook = Playbook(tl, logs=True)
    assert (
            playbook
            << Log("Got start. Server state: CLOSED")
            >> DataReceived(tctx.client, b"open")
            << OpenConnection(server)
    )
    assert tl.tunnel_state is tunnel.TunnelState.ESTABLISHING
    assert (
            playbook
            >> reply("IPoAC packet dropped.")
            << Log("Opened: err='IPoAC packet dropped.'. Server state: CLOSED")
    )
    assert tl.tunnel_state is tunnel.TunnelState.CLOSED


@pytest.mark.parametrize("disconnect", ["client", "server"])
def test_disconnect_during_handshake_start(tctx: Context, disconnect):
    server = Server(("proxy", 1234))
    server.state = ConnectionState.OPEN

    tl = TTunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)

    playbook = Playbook(tl, logs=True)

    assert (
            playbook
            << SendData(server, b"handshake-hello")
    )
    if disconnect == "client":
        assert (
                playbook
                >> ConnectionClosed(tctx.client)
                >> ConnectionClosed(server)  # proxyserver will cancel all other connections as well.
                << CloseConnection(server)
                << Log("Got start. Server state: CLOSED")
                << Log("Got client close.")
                << CloseConnection(tctx.client)
        )
    else:
        assert (
                playbook
                >> ConnectionClosed(server)
                << CloseConnection(server)
                << Log("Got start. Server state: CLOSED")
        )


@pytest.mark.parametrize("disconnect", ["client", "server"])
def test_disconnect_during_handshake_command(tctx: Context, disconnect):
    server = Server(("proxy", 1234))

    tl = TTunnelLayer(tctx, server, tctx.server)
    tl.child_layer = TChildLayer(tctx)

    playbook = Playbook(tl, logs=True)
    assert (
            playbook
            << Log("Got start. Server state: CLOSED")
            >> DataReceived(tctx.client, b"client-hello")
            << SendData(tctx.client, b"client-hello-reply")
            >> DataReceived(tctx.client, b"open")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"handshake-hello")
    )
    if disconnect == "client":
        assert (
                playbook
                >> ConnectionClosed(tctx.client)
                >> ConnectionClosed(server)  # proxyserver will cancel all other connections as well.
                << CloseConnection(server)
                << Log("Opened: err='connection closed'. Server state: CLOSED")
                << Log("Got client close.")
                << CloseConnection(tctx.client)
        )
    else:
        assert (
                playbook
                >> ConnectionClosed(server)
                << CloseConnection(server)
                << Log("Opened: err='connection closed'. Server state: CLOSED")
        )


def test_layer_stack(tctx):
    stack = tunnel.LayerStack()
    a = TChildLayer(tctx)
    b = TChildLayer(tctx)
    stack /= a
    stack /= b
    assert stack[0] == a
    assert a.child_layer is b

    stack2 = tunnel.LayerStack()
    stack2 /= TChildLayer(tctx)
    stack2 /= stack
    assert stack2[0].child_layer is a  # type: ignore
