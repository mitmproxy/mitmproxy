import socket
import struct
from abc import ABCMeta
from typing import Optional

from mitmproxy import platform
from mitmproxy.net import server_spec
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.layers import tls
from mitmproxy.proxy.utils import expect


class HttpProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class DestinationKnown(layer.Layer, metaclass=ABCMeta):
    """Base layer for layers that gather connection destination info and then delegate."""
    child_layer: layer.Layer

    def finish_start(self) -> layer.CommandGenerator[Optional[str]]:
        if self.context.options.connection_strategy == "eager" and self.context.server.address:
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
        spec = server_spec.parse_with_mode(self.context.options.mode)[1]
        self.context.server.address = spec.address

        if spec.scheme not in ("http", "tcp"):
            if not self.context.options.keep_host_header:
                self.context.server.sni = spec.address[0]
            self.child_layer = tls.ServerTLSLayer(self.context)
        else:
            self.child_layer = layer.NextLayer(self.context)

        err = yield from self.finish_start()
        if err:
            yield commands.CloseConnection(self.context.client)


class TransparentProxy(DestinationKnown):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert platform.original_addr is not None
        socket = yield commands.GetSocket(self.context.client)
        try:
            self.context.server.address = platform.original_addr(socket)
        except Exception as e:
            yield commands.Log(f"Transparent mode failure: {e!r}")

        self.child_layer = layer.NextLayer(self.context)

        err = yield from self.finish_start()
        if err:
            yield commands.CloseConnection(self.context.client)


SOCKS5_VERSION = 0x05

SOCKS5_METHOD_NO_AUTHENTICATION_REQUIRED = 0x00
SOCKS5_METHOD_NO_ACCEPTABLE_METHODS = 0xFF

SOCKS5_ATYP_IPV4_ADDRESS = 0x01
SOCKS5_ATYP_DOMAINNAME = 0x03
SOCKS5_ATYP_IPV6_ADDRESS = 0x04

SOCKS5_REP_HOST_UNREACHABLE = 0x04
SOCKS5_REP_COMMAND_NOT_SUPPORTED = 0x07
SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


class Socks5Proxy(DestinationKnown):
    buf: bytes = b""
    greeted: bool = False

    def socks_err(
        self,
        message: str,
        reply_code: Optional[int] = None,
    ) -> layer.CommandGenerator[None]:
        if reply_code is not None:
            yield commands.SendData(
                self.context.client,
                bytes([SOCKS5_VERSION, reply_code]) + b"\x00\x01\x00\x00\x00\x00\x00\x00"
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

            if not self.greeted:
                # Parse Client Greeting
                if len(self.buf) < 2:
                    return

                if self.buf[0] != SOCKS5_VERSION:
                    if self.buf[:3].isupper():
                        guess = "Probably not a SOCKS request but a regular HTTP request. "
                    else:
                        guess = ""
                    yield from self.socks_err(guess + "Invalid SOCKS version. Expected 0x05, got 0x%x" % self.buf[0])
                    return

                n_methods = self.buf[1]
                if len(self.buf) < 2 + n_methods:
                    return
                if SOCKS5_METHOD_NO_AUTHENTICATION_REQUIRED not in self.buf[2:2 + n_methods]:
                    yield from self.socks_err("mitmproxy only supports SOCKS without authentication",
                                              SOCKS5_METHOD_NO_ACCEPTABLE_METHODS)
                    return

                # Send Server Greeting
                # Ver = SOCKS5, Auth = NO_AUTH
                yield commands.SendData(self.context.client, b"\x05\x00")
                self.buf = self.buf[2 + n_methods:]
                self.greeted = True

            # Parse Connect Request
            if len(self.buf) < 4:
                return

            if self.buf[:3] != b"\x05\x01\x00":
                yield from self.socks_err(f"Unsupported SOCKS5 request: {self.buf!r}", SOCKS5_REP_COMMAND_NOT_SUPPORTED)
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
                yield from self.socks_err(f"Unknown address type: {atyp}", SOCKS5_REP_ADDRESS_TYPE_NOT_SUPPORTED)
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

            port, = struct.unpack("!H", msg[-2:])

            # We now have all we need, let's get going.
            self.context.server.address = (host, port)
            self.child_layer = layer.NextLayer(self.context)

            # this already triggers the child layer's Start event,
            # but that's not a problem in practice...
            err = yield from self.finish_start()
            if err:
                yield commands.SendData(self.context.client, b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
                yield commands.CloseConnection(self.context.client)
            else:
                yield commands.SendData(self.context.client, b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                if self.buf:
                    yield from self.child_layer.handle_event(events.DataReceived(self.context.client, self.buf))
                    del self.buf

        elif isinstance(event, events.ConnectionClosed):
            if self.buf:
                yield commands.Log(f"Client closed connection before completing SOCKS5 handshake: {self.buf!r}")
            yield commands.CloseConnection(event.connection)
        else:
            raise AssertionError(f"Unknown event: {event}")
