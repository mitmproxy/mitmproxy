from __future__ import annotations

import logging
import socket
import struct
import sys
from abc import ABCMeta
from collections.abc import Callable
from dataclasses import dataclass

from mitmproxy import connection
from mitmproxy.connection import Address
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.mode_specs import ReverseMode
from mitmproxy.proxy.utils import expect

if sys.version_info < (3, 11):
    from typing_extensions import assert_never
else:
    from typing import assert_never


class HttpProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class HttpUpstreamProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class DestinationKnown(layer.Layer, metaclass=ABCMeta):
    """Base layer for layers that gather connection destination info and then delegate."""

    child_layer: layer.Layer

    def finish_start(self) -> layer.CommandGenerator[str | None]:
        if (
            self.context.options.connection_strategy == "eager"
            and self.context.server.address
            and self.context.server.transport_protocol == "tcp"
        ):
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self._handle_event = self.done  # type: ignore
                return err

        self._handle_event = self.child_layer.handle_event  # type: ignore
        yield from self.child_layer.handle_event(events.Start())
        return None

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()


class ReverseProxy(DestinationKnown):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        spec = self.context.client.proxy_mode
        assert isinstance(spec, ReverseMode)
        self.context.server.address = spec.address

        self.child_layer = layer.NextLayer(self.context)

        # For secure protocols, set SNI if keep_host_header is false
        match spec.scheme:
            case "http3" | "quic" | "https" | "tls" | "dtls":
                if not self.context.options.keep_host_header:
                    self.context.server.sni = spec.address[0]
            case "tcp" | "http" | "udp" | "dns":
                pass
            case _:  # pragma: no cover
                assert_never(spec.scheme)

        err = yield from self.finish_start()
        if err:
            yield commands.CloseConnection(self.context.client)


class TransparentProxy(DestinationKnown):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.context.server.address, "No server address set."
        self.child_layer = layer.NextLayer(self.context)
        err = yield from self.finish_start()
        if err:
            yield commands.CloseConnection(self.context.client)


SOCKS5_VERSION = 0x05

SOCKS5_METHOD_NO_AUTHENTICATION_REQUIRED = 0x00
SOCKS5_METHOD_USER_PASSWORD_AUTHENTICATION = 0x02
SOCKS5_METHOD_NO_ACCEPTABLE_METHODS = 0xFF

SOCKS5_CMD_CONNECT = 0x01
SOCKS5_CMD_BIND = 0x02
SOCKS5_CMD_UDP_ASSOCIATE = 0x03

SOCKS5_ATYP_IPV4_ADDRESS = 0x01
SOCKS5_ATYP_DOMAINNAME = 0x03
SOCKS5_ATYP_IPV6_ADDRESS = 0x04

SOCKS5_REP_SUCCEEDED = 0x00
SOCKS5_REP_GENERAL_FAILURE = 0x01
SOCKS5_REP_HOST_UNREACHABLE = 0x04
SOCKS5_REP_COMMAND_NOT_SUPPORTED = 0x07
SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


class Socks5Error(Exception):
    """A SOCKS5 message could not be parsed."""

    def __init__(self, message: str, reply_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.reply_code = reply_code


def parse_socks5_address(data: bytes, offset: int = 0) -> tuple[str, int, int] | None:
    """
    Parse the ATYP + DST.ADDR + DST.PORT fields of a SOCKS5 message, starting at `offset`.

    Returns a `(host, port, end_offset)` tuple where `end_offset` points just past the
    parsed fields, or `None` if more data is needed to parse the address.
    Raises `Socks5Error` if the address type is not supported.
    """
    if len(data) < offset + 1:
        return None
    atyp = data[offset]
    if atyp == SOCKS5_ATYP_IPV4_ADDRESS:
        length = 1 + 4 + 2
    elif atyp == SOCKS5_ATYP_IPV6_ADDRESS:
        length = 1 + 16 + 2
    elif atyp == SOCKS5_ATYP_DOMAINNAME:
        if len(data) < offset + 2:
            return None
        length = 1 + 1 + data[offset + 1] + 2
    else:
        raise Socks5Error(
            f"Unknown address type: {atyp}", SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED
        )

    end = offset + length
    if len(data) < end:
        return None

    if atyp == SOCKS5_ATYP_IPV4_ADDRESS:
        host = socket.inet_ntop(socket.AF_INET, data[offset + 1 : offset + 5])
    elif atyp == SOCKS5_ATYP_IPV6_ADDRESS:
        host = socket.inet_ntop(socket.AF_INET6, data[offset + 1 : offset + 17])
    else:
        host = data[offset + 2 : end - 2].decode("ascii", "replace")
    (port,) = struct.unpack("!H", data[end - 2 : end])
    return host, port, end


def pack_socks5_address(host: str, port: int) -> bytes:
    """Encode an address as the SOCKS5 ATYP + ADDR + PORT fields."""
    try:
        packed = socket.inet_pton(socket.AF_INET, host)
        atyp = SOCKS5_ATYP_IPV4_ADDRESS
    except OSError:
        try:
            packed = socket.inet_pton(socket.AF_INET6, host)
            atyp = SOCKS5_ATYP_IPV6_ADDRESS
        except OSError:
            encoded = host.encode("idna")
            packed = bytes([len(encoded)]) + encoded
            atyp = SOCKS5_ATYP_DOMAINNAME
    return bytes([atyp]) + packed + struct.pack("!H", port)


@dataclass
class Socks5AuthData:
    client_conn: connection.Client
    username: str
    password: str
    valid: bool = False


@dataclass
class Socks5AuthHook(StartHook):
    """
    Mitmproxy has received username/password SOCKS5 credentials.

    This hook decides whether they are valid by setting `data.valid`.
    """

    data: Socks5AuthData


class Socks5Proxy(DestinationKnown):
    buf: bytes = b""

    def socks_err(
        self,
        message: str,
        reply_code: int | None = None,
    ) -> layer.CommandGenerator[None]:
        if reply_code is not None:
            yield commands.SendData(
                self.context.client,
                bytes([SOCKS5_VERSION, reply_code])
                + b"\x00\x01\x00\x00\x00\x00\x00\x00",
            )
        yield commands.CloseConnection(self.context.client)
        yield commands.Log(message)
        self._handle_event = self.done

    @expect(events.Start, events.DataReceived, events.ConnectionClosed)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            pass
        elif isinstance(event, events.DataReceived):
            self.buf += event.data
            yield from self.state()
        elif isinstance(event, events.ConnectionClosed):
            if self.buf:
                yield commands.Log(
                    f"Client closed connection before completing SOCKS5 handshake: {self.buf!r}"
                )
            yield commands.CloseConnection(event.connection)
        else:
            raise AssertionError(f"Unknown event: {event}")

    def state_greet(self) -> layer.CommandGenerator[None]:
        if len(self.buf) < 2:
            return

        if self.buf[0] != SOCKS5_VERSION:
            if self.buf[:3].isupper():
                guess = "Probably not a SOCKS request but a regular HTTP request. "
            else:
                guess = ""
            yield from self.socks_err(
                guess + "Invalid SOCKS version. Expected 0x05, got 0x%x" % self.buf[0]
            )
            return

        n_methods = self.buf[1]
        if len(self.buf) < 2 + n_methods:
            return

        if "proxyauth" in self.context.options and self.context.options.proxyauth:
            method = SOCKS5_METHOD_USER_PASSWORD_AUTHENTICATION
            self.state = self.state_auth
        else:
            method = SOCKS5_METHOD_NO_AUTHENTICATION_REQUIRED
            self.state = self.state_connect

        if method not in self.buf[2 : 2 + n_methods]:
            method_str = (
                "user/password"
                if method == SOCKS5_METHOD_USER_PASSWORD_AUTHENTICATION
                else "no"
            )
            yield from self.socks_err(
                f"Client does not support SOCKS5 with {method_str} authentication.",
                SOCKS5_METHOD_NO_ACCEPTABLE_METHODS,
            )
            return
        yield commands.SendData(self.context.client, bytes([SOCKS5_VERSION, method]))
        self.buf = self.buf[2 + n_methods :]
        yield from self.state()

    state: Callable[..., layer.CommandGenerator[None]] = state_greet

    def state_auth(self) -> layer.CommandGenerator[None]:
        if len(self.buf) < 3:
            return

        # Parsing username and password, which is somewhat atrocious
        user_len = self.buf[1]
        if len(self.buf) < 3 + user_len:
            return
        pass_len = self.buf[2 + user_len]
        if len(self.buf) < 3 + user_len + pass_len:
            return
        user = self.buf[2 : (2 + user_len)].decode("utf-8", "backslashreplace")
        password = self.buf[(3 + user_len) : (3 + user_len + pass_len)].decode(
            "utf-8", "backslashreplace"
        )

        data = Socks5AuthData(self.context.client, user, password)
        yield Socks5AuthHook(data)
        if not data.valid:
            # The VER field contains the current **version of the subnegotiation**, which is X'01'.
            yield commands.SendData(self.context.client, b"\x01\x01")
            yield from self.socks_err("authentication failed")
            return

        yield commands.SendData(self.context.client, b"\x01\x00")
        self.buf = self.buf[3 + user_len + pass_len :]
        self.state = self.state_connect
        yield from self.state()

    def state_connect(self) -> layer.CommandGenerator[None]:
        # Parse the request: VER CMD RSV ATYP DST.ADDR DST.PORT
        if len(self.buf) < 5:
            return

        cmd = self.buf[1]
        supported_cmds = (SOCKS5_CMD_CONNECT, SOCKS5_CMD_UDP_ASSOCIATE)
        if (
            self.buf[0] != SOCKS5_VERSION
            or self.buf[2] != 0x00
            or cmd not in supported_cmds
        ):
            yield from self.socks_err(
                f"Unsupported SOCKS5 request: {self.buf!r}",
                SOCKS5_REP_COMMAND_NOT_SUPPORTED,
            )
            return

        try:
            parsed = parse_socks5_address(self.buf, 3)
        except Socks5Error as e:
            yield from self.socks_err(e.message, e.reply_code)
            return
        if parsed is None:
            return  # not enough bytes yet
        host, port, offset = parsed
        self.buf = self.buf[offset:]

        if cmd == SOCKS5_CMD_UDP_ASSOCIATE:
            yield from self.start_udp_associate()
            return

        # CONNECT: We now have all we need, let's get going.
        self.context.server.address = (host, port)
        self.child_layer = layer.NextLayer(self.context)

        # this already triggers the child layer's Start event,
        # but that's not a problem in practice...
        err = yield from self.finish_start()
        if err:
            yield commands.SendData(
                self.context.client, b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00"
            )
            yield commands.CloseConnection(self.context.client)
        else:
            yield commands.SendData(
                self.context.client, b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            )
            if self.buf:
                yield from self.child_layer.handle_event(
                    events.DataReceived(self.context.client, self.buf)
                )
                del self.buf

    def start_udp_associate(self) -> layer.CommandGenerator[None]:
        # Point the client at our UDP relay, which shares this connection's address:port.
        assert self.context.client.sockname
        host, port = self.context.client.sockname[:2]
        yield commands.SendData(
            self.context.client,
            bytes([SOCKS5_VERSION, SOCKS5_REP_SUCCEEDED, 0x00])
            + pack_socks5_address(host, port),
        )
        self.buf = b""
        self.state = self.state_associated

    def state_associated(self) -> layer.CommandGenerator[None]:
        # The control connection is idle while associated; datagrams flow over the relay.
        self.buf = b""
        yield from ()


class Socks5UdpStreamLayer(layer.Layer):
    """
    Virtual layer for a single destination of a SOCKS5 UDP association. Like
    `QuicStreamLayer`, it owns virtual client/server connections and relays all events to
    a child `NextLayer` stack.
    """

    client: connection.Client
    server: connection.Server
    child_layer: layer.Layer
    header: bytes

    def __init__(self, context: Context, address: Address, header: bytes) -> None:
        self.client = context.client = context.client.copy()
        self.client.transport_protocol = "udp"
        self.client.state = connection.ConnectionState.OPEN
        self.server = context.server = connection.Server(
            address=address, transport_protocol="udp"
        )
        self.header = header
        super().__init__(context)
        self.child_layer = layer.NextLayer(context)

        # we don't handle any events ourselves, everything goes to the child layer.
        self.handle_event = self.child_layer.handle_event  # type: ignore
        self._handle_event = self.child_layer._handle_event  # type: ignore

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        raise AssertionError  # pragma: no cover


class Socks5UdpProxy(layer.Layer):
    """
    Relay for SOCKS5 UDP ASSOCIATE datagrams, the receiving end of the relay that
    `Socks5Proxy` advertises. Each datagram is prefixed with a SOCKS5 UDP request header
    (RSV, FRAG, ATYP, DST.ADDR, DST.PORT). We strip the header, de-multiplex by destination
    into a `Socks5UdpStreamLayer`, and re-encapsulate replies back to the client.
    """

    connections: dict[connection.Connection, layer.Layer]
    destinations: dict[Address, Socks5UdpStreamLayer]
    command_sources: dict[commands.Command, layer.Layer]

    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.connections = {}
        self.destinations = {}
        self.command_sources = {}

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            # destinations are discovered per datagram, so there is nothing to do yet.
            yield from ()
        elif isinstance(event, events.CommandCompleted):
            yield from self.event_to_child(
                self.command_sources.pop(event.command), event
            )
        elif isinstance(event, events.MessageInjected):
            yield from self.event_to_child(
                self.connections[event.flow.client_conn], event
            )
        elif (
            isinstance(event, events.DataReceived)
            and event.connection is self.context.client
        ):
            yield from self.handle_datagram(event.data)
        elif (
            isinstance(event, events.ConnectionClosed)
            and event.connection is self.context.client
        ):
            for stream in list(self.destinations.values()):
                yield from self.event_to_child(
                    stream, events.ConnectionClosed(stream.client)
                )
            self._handle_event = self.done  # type: ignore
        elif isinstance(event, events.ConnectionEvent):
            yield from self.event_to_child(self.connections[event.connection], event)
        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def handle_datagram(self, data: bytes) -> layer.CommandGenerator[None]:
        if len(data) < 4 or data[:2] != b"\x00\x00":
            yield commands.Log(
                f"Received invalid SOCKS5 UDP datagram: {data!r}", logging.DEBUG
            )
            return
        if data[2] != 0x00:
            # FRAG != 0, datagram reassembly is not supported.
            yield commands.Log(
                f"Dropping fragmented SOCKS5 UDP datagram: {data!r}", logging.DEBUG
            )
            return
        try:
            parsed = parse_socks5_address(data, 3)
        except Socks5Error as e:
            yield commands.Log(
                f"Dropping SOCKS5 UDP datagram: {e.message}", logging.DEBUG
            )
            return
        if parsed is None:
            yield commands.Log(
                f"Received truncated SOCKS5 UDP datagram: {data!r}", logging.DEBUG
            )
            return
        host, port, offset = parsed
        address = (host, port)

        stream = self.destinations.get(address)
        if stream is None:
            # the request header (data[:offset]) is reused to encapsulate replies.
            stream = Socks5UdpStreamLayer(self.context.fork(), address, data[:offset])
            self.destinations[address] = stream
            self.connections[stream.client] = stream
            self.connections[stream.server] = stream
            yield from self.event_to_child(stream, events.Start())
        yield from self.event_to_child(
            stream, events.DataReceived(stream.client, data[offset:])
        )

    def event_to_child(
        self, stream: layer.Layer, event: events.Event
    ) -> layer.CommandGenerator[None]:
        for command in stream.handle_event(event):
            if (
                isinstance(stream, Socks5UdpStreamLayer)
                and isinstance(command, commands.ConnectionCommand)
                and command.connection is stream.client
            ):
                if isinstance(command, commands.SendData):
                    yield commands.SendData(
                        self.context.client, stream.header + command.data
                    )
                elif isinstance(command, commands.CloseConnection):
                    # there is no client close to forward, just forget this destination.
                    self.destinations.pop(stream.server.address, None)  # type: ignore
                    self.connections.pop(stream.client, None)
                    self.connections.pop(stream.server, None)
                else:
                    raise AssertionError(
                        f"Unexpected stream client command: {command!r}"
                    )
            else:
                if command.blocking or isinstance(command, commands.RequestWakeup):
                    self.command_sources[command] = stream
                if isinstance(command, commands.OpenConnection):
                    self.connections[command.connection] = stream
                yield command

    def done(self, _) -> layer.CommandGenerator[None]:  # pragma: no cover
        yield from ()
