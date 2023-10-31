from __future__ import annotations

import socket
import struct
import sys
from abc import ABCMeta
from collections.abc import Callable
from dataclasses import dataclass

from mitmproxy import connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
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

SOCKS5_ATYP_IPV4_ADDRESS = 0x01
SOCKS5_ATYP_DOMAINNAME = 0x03
SOCKS5_ATYP_IPV6_ADDRESS = 0x04

SOCKS5_REP_HOST_UNREACHABLE = 0x04
SOCKS5_REP_COMMAND_NOT_SUPPORTED = 0x07
SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


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
        # Parse Connect Request
        if len(self.buf) < 5:
            return

        if self.buf[:3] != b"\x05\x01\x00":
            yield from self.socks_err(
                f"Unsupported SOCKS5 request: {self.buf!r}",
                SOCKS5_REP_COMMAND_NOT_SUPPORTED,
            )
            return

        # Determine message length
        atyp = self.buf[3]
        message_len: int
        if atyp == SOCKS5_ATYP_IPV4_ADDRESS:
            message_len = 4 + 4 + 2
        elif atyp == SOCKS5_ATYP_IPV6_ADDRESS:
            message_len = 4 + 16 + 2
        elif atyp == SOCKS5_ATYP_DOMAINNAME:
            message_len = 4 + 1 + self.buf[4] + 2
        else:
            yield from self.socks_err(
                f"Unknown address type: {atyp}", SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED
            )
            return

        # Do we have enough bytes yet?
        if len(self.buf) < message_len:
            return

        # Parse host and port
        msg, self.buf = self.buf[:message_len], self.buf[message_len:]

        host: str
        if atyp == SOCKS5_ATYP_IPV4_ADDRESS:
            host = socket.inet_ntop(socket.AF_INET, msg[4:-2])
        elif atyp == SOCKS5_ATYP_IPV6_ADDRESS:
            host = socket.inet_ntop(socket.AF_INET6, msg[4:-2])
        else:
            host_bytes = msg[5:-2]
            host = host_bytes.decode("ascii", "replace")

        (port,) = struct.unpack("!H", msg[-2:])

        # We now have all we need, let's get going.
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
