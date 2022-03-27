from __future__ import annotations

import asyncio
from asyncio import base_events
from collections import deque
import ipaddress
import socket
import struct
from typing import Any, Deque, Dict, Optional, Tuple, Union
from mitmproxy import ctx


Address = Union[Tuple[str, int], Tuple[str, int, int, int]]


IP_RECVORIGDSTADDR = getattr(socket, "IP_RECVORIGDSTADDR", 20)
MAX_UDP_PACKET_SIZE = 65535 - 20


async def _resolve_addr(loop: asyncio.AbstractEventLoop, host: str, port: int) -> Tuple[socket.AddressFamily, Address]:
    """Resolve a host and port into an address."""
    if not host:
        return socket.AddressFamily.AF_INET, ("127.0.0.1", port)
    for addrinfo in await loop.getaddrinfo(host, port):
        family, _, _, _, addr = addrinfo
        return family, addr
    raise LookupError(f"address of host '{host}' not found")


def _unpack_addr(sockaddr_in: bytes) -> Address:
    """Converts a native sockaddr into address and port tuple."""
    addr: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    (family,) = struct.unpack_from("h", sockaddr_in, 0)
    if family == socket.AF_INET:
        port, in4_addr, _ = struct.unpack_from("!H4s8s", sockaddr_in, 2)
        addr = ipaddress.IPv4Address(in4_addr)
    elif family == socket.AF_INET6:
        port, _, in6_addr, _ = struct.unpack_from("!H16sL", sockaddr_in, 2)
        addr = ipaddress.IPv6Address(in6_addr)
    else:
        raise NotImplementedError(f"family {family} not implemented")
    return str(addr), port


def _recvfrom_transparent(sock: socket.socket, bufsize: int, flags: int = 0) -> Tuple[bytes, Tuple[Address, Address]]:
    """Same as recvfrom, but always returns source and destination addresses."""
    server_addr: Optional[Address] = None
    recvmsg = getattr(sock, "recvmsg")
    if not recvmsg:
        raise NotImplementedError("Transparent UDP sockets are so far only implemented on platforms supporting recvmsg.")
    data, ancdata, _, client_addr = recvmsg(sock, bufsize, socket.CMSG_SPACE(50), flags)
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_IP and cmsg_type == IP_RECVORIGDSTADDR:
            server_addr = _unpack_addr(cmsg_data)
            break
    return data, (client_addr, sock.getsockname() if server_addr is None else server_addr)


class UdpServer(base_events.Server, asyncio.DatagramProtocol):
    """UDP server that emulates connection-oriented behavior."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        sock: socket.socket,
        client_connected_cb: asyncio.streams._ClientConnectedCallback,
        transparent: bool,
    ):
        self._socket = sock
        self._client_connected_cb = client_connected_cb
        self._transparent = transparent
        self._connections: Dict[Tuple[Address, Address], UdpServerConnection] = dict()
        self._create_task: Optional[asyncio.Task] = None
        self._transport: Optional[asyncio.BaseTransport] = None
        super().__init__(
            loop=loop,
            sockets=[self._socket],
            protocol_factory=lambda: self,  # unused
            ssl_context=None,  # unused
            backlog=0,  # unused
            ssl_handshake_timeout=None,  # unused
        )

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        # store the transport
        # NOTE we don't write on this transport, so no need to wrap it
        assert self._transport is None
        self._transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # log any exception and close the server
        if exc is not None:
            ctx.log.error(f"server {self!r} has encountered an error: {exc!r}")
        self.close()

    def datagram_received(self, data: bytes, addr: Any) -> None:
        # forward the packet to the matching connection (possibly creating it)
        if not self._transparent:
            addr = (addr, self._socket.getsockname())
        client_addr, server_addr = addr
        conn = self._connections[addr] if addr in self._connections else self._connections.setdefault(
            addr,
            UdpServerConnection(
                server=self,
                client_addr=client_addr,
                server_addr=server_addr,
                client_connected_cb=self._client_connected_cb,
            ),
        )
        conn.datagram_received(data, client_addr)

    def error_received(self, exc: Exception) -> None:
        # if recv[msg] throws an error, we simulate a connection_lost
        self.connection_lost(exc)

    def _start_serving(self) -> None:
        if self.is_serving():
            return
        self._serving = True
        loop = self.get_loop()
        self._create_task = loop.create_task(loop.create_datagram_endpoint(lambda: self, sock=self._socket))

    def close(self) -> None:
        # stop the creation of the transport and close the transport itself
        if self._create_task is not None and not self._create_task.done():
            self._create_task.cancel()
            self._create_task = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        super().close()


class UdpStreamReader(asyncio.StreamReader):
    """StreamReader that only supports reading entire packets."""

    MARKER = b'\xFF'

    def __init__(self, loop: asyncio.events.AbstractEventLoop) -> None:
        super().__init__(limit=100 * len(self.MARKER), loop=loop)  # here limit is the amount of packets
        self._packets: Deque[bytes] = deque()

    def feed_data(self, data: bytes) -> None:
        size = len(data)
        if size > MAX_UDP_PACKET_SIZE:
            raise ValueError(f"packet of size {size} bytes exceeds limit of {MAX_UDP_PACKET_SIZE} byte")

        # add only a marker in the base class and queue the packet in this class
        # NOTE empty packets will also notify any waiter which is on purpose
        super().feed_data(self.MARKER)
        self._packets.append(data)

    async def readline(self) -> bytes:
        raise NotImplementedError()

    async def readuntil(self, _: bytes = b'\n') -> bytes:
        raise NotImplementedError()

    async def read(self, n=-1) -> bytes:
        if n < MAX_UDP_PACKET_SIZE:
            raise ValueError(f"read size must be at least {MAX_UDP_PACKET_SIZE} bytes")

        # read the next marker from the base class, which is one packet
        data = await super().read(len(self.MARKER))
        if not data:
            return data
        assert data == self.MARKER
        return self._packets.popleft()

    async def readexactly(self, _: int) -> bytes:
        raise NotImplementedError()


class UdpServerConnection(asyncio.DatagramProtocol, asyncio.StreamReaderProtocol):
    """Client-initiated UDP connection."""

    def __init__(
        self,
        server: UdpServer,
        client_addr: Address,
        server_addr: Address,
        client_connected_cb: asyncio.streams._ClientConnectedCallback
    ):
        self._server = server
        self._client_addr = client_addr
        self._server_addr = server_addr

        loop = server.get_loop()
        super().__init__(
            stream_reader=UdpStreamReader(loop),
            client_connected_cb=client_connected_cb,
            loop=loop,
        )

        sock = socket.socket(
            family=socket.AddressFamily.AF_INET6 if len(server_addr) == 4 else socket.AddressFamily.AF_INET,
            type=socket.SocketKind.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP,
        )
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if server._transparent:
                sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)
            sock.bind(server_addr)
            sock.connect(client_addr)
            loop.create_task(loop.create_datagram_endpoint(lambda: self, sock=sock))
        except:
            sock.close()
            raise

    def datagram_received(self, data: bytes, addr: Address) -> None:
        # between bind and connect we can receive other packets, route them accordingly
        if addr == self._client_addr:
            self.data_received(data)
        else:
            self._server.datagram_received(data, (addr, self._server_addr) if self._server._transparent else addr)

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        # wrap the transport as writeable
        super().connection_made(UdpWriteTransport(transport, self._client_addr))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # remove the connection from the server
        del self._server._connections[(self._client_addr, self._server_addr)]
        super().connection_lost(exc)

    def error_received(self, exc: Exception) -> None:
        # on error we're closing the connection
        self.connection_lost(exc)


class UdpWriteTransport(asyncio.WriteTransport, asyncio.DatagramTransport):
    """Wrapper around a asyncio.DatagramTransport to support write via sendto."""

    # TODO forward other methods as well if supported

    def __init__(self, inner: asyncio.BaseTransport, addr: Address):
        assert isinstance(inner, asyncio.DatagramTransport)
        self._inner = inner
        self._addr = addr

    def get_extra_info(self, name: Any, default: Any = None) -> Any:
        return self._inner.get_extra_info(name, default)

    def is_closing(self) -> bool:
        return self._inner.is_closing()

    def close(self) -> None:
        self._inner.close()

    def set_protocol(self, protocol: asyncio.BaseProtocol) -> None:
        self._inner.set_protocol(protocol)

    def get_protocol(self) -> asyncio.BaseProtocol:
        return self._inner.get_protocol()

    def write(self, data: Any) -> None:
        self._inner.sendto(data, self._addr)

    def sendto(self, data: Any, addr: Optional[Union[Tuple[Any, ...], str]] = None) -> None:
        if addr is not None and addr != (self._addr[0] if isinstance(addr, str) else self._addr):
            raise ValueError(f"asked to send to '{addr}', but only '{self._addr}' allowed")
        self.write(data)

    def abort(self) -> None:
        self._inner.abort()


class UdpOutgoingProtocol(asyncio.StreamReaderProtocol, asyncio.DatagramProtocol):
    """UDP protocol for server-initiated connections."""

    def __init__(self, filter_addr: Address, reader: asyncio.StreamReader, loop: asyncio.AbstractEventLoop):
        self._filter_addr = filter_addr
        super().__init__(reader, loop=loop)

    def datagram_received(self, data: bytes, addr: Address) -> None:
        # between bind and connect we can receive other packets, drop invalid ones
        if addr == self._filter_addr:
            self.data_received(data)

    def error_received(self, exc: Exception) -> None:
        # on error we're closing the connection
        self.connection_lost(exc)


async def start_server(
    client_connected_cb: asyncio.streams._ClientConnectedCallback,
    host: str,
    port: int,
    *,
    transparent: bool = False,
) -> base_events.Server:
    """UDP variant of asyncio.start_server."""

    loop = asyncio.events.get_event_loop()
    family, addr = await _resolve_addr(loop, host, port)
    sock = socket.socket(family=family, type=socket.SocketKind.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if transparent:
            sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)
            sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
            setattr(sock, "recvfrom", _recvfrom_transparent)
        sock.bind(addr)
    except:
        sock.close()
        raise
    server = UdpServer(loop=loop, sock=sock, client_connected_cb=client_connected_cb, transparent=transparent)
    server._start_serving()
    return server


async def open_connection(host: str, port: int) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """UDP variant of asyncio.open_connection."""

    loop = asyncio.events.get_event_loop()
    family, addr = await _resolve_addr(loop, host, port)
    reader = UdpStreamReader(loop)
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UdpOutgoingProtocol(addr, reader, loop),
        family=family,
        remote_addr=addr[0:2]
    )
    writer = asyncio.StreamWriter(UdpWriteTransport(transport, addr), protocol, reader, loop)
    return reader, writer
