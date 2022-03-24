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


def _recvfrom_transparent(sock: socket.socket, bufsize: int, flags: int = ...) -> Tuple[bytes, Tuple[Address, Address]]:
    """Same as recvfrom, but always returns source and destination addresses."""
    server_addr: Address = None
    data, ancdata, _, client_addr = sock.recvmsg(bufsize, socket.CMSG_LEN(50), flags)
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_IP and cmsg_type == IP_RECVORIGDSTADDR:
            server_addr = _unpack_addr(cmsg_data)
            break
    return data, (client_addr, sock.getsockname() if server_addr is None else server_addr)


class UdpServer(base_events.Server, asyncio.DatagramProtocol):
    """UDP server that emulates connection-oriented behavior."""

    _client_connected_cb: asyncio.streams._ClientConnectedCallback
    _connections: Dict[Tuple[Address, Address], UdpServerConnection]
    _create_task: Optional[asyncio.Task]
    _socket: socket.socket
    _transparent: bool
    _transport: Optional[asyncio.DatagramTransport]

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        sock: socket.socket,
        client_connected_cb: asyncio.streams._ClientConnectedCallback,
        transparent: bool,
    ):
        self._client_connected_cb = client_connected_cb
        self._connections = dict()
        self._create_task = None
        self._socket = sock
        self._transparent = transparent
        self._transport = None
        super().__init__(
            loop=loop,
            sockets=[self._socket],
            protocol_factory=None,  # unused
            ssl_context=None,  # unused
            backlog=None,  # unused
            ssl_handshake_timeout=None,  # unused
        )

    def is_transparent(self) -> bool:
        return self._transparent

    def connection_made(self, transport):
        # store the transport
        assert self._transport is None
        self._transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # log any exception and close the server
        if exc is not None:
            ctx.log.error(f"server {self!r} has encountered an error: {exc!r}")
        self.close()

    def datagram_received(self, data: bytes, addr: Tuple[Address, Address]) -> None:
        # forward the packet to the matching connection (possibly creating it)
        client_addr, server_addr = addr if self._transparent else addr, self._socket.getsockname()
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
        if self._serving:
            return
        self._serving = True
        loop = self.get_loop()
        self._create_task = loop.create_task(loop.create_datagram_endpoint(lambda: self, sock=self._socket))

    def close(self):
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

    _marker = b'\xFF'
    _packets: Deque[bytes]

    def __init__(self, loop: asyncio.events.AbstractEventLoop) -> None:
        super().__init__(limit=100 * len(self._marker), loop=loop)  # here limit is the amount of packets
        self._packets = deque()

    def feed_data(self, data: bytes) -> None:
        size = len(data)
        if size > MAX_UDP_PACKET_SIZE:
            raise ValueError(f"packet of size {size} bytes exceeds limit of {MAX_UDP_PACKET_SIZE} byte")

        # add only a marker in the base class and queue the packet in this class
        # NOTE empty packets will also notify any waiter which is on purpose
        super().feed_data(self._marker)
        self._packets.append(data)

    async def readline(self) -> bytes:
        raise NotImplementedError()

    async def readuntil(self, _: bytes = b'\n') -> bytes:
        raise NotImplementedError()

    async def read(self, n=-1) -> bytes:
        if n < MAX_UDP_PACKET_SIZE:
            raise ValueError(f"read size must be at least {MAX_UDP_PACKET_SIZE} bytes")

        # read the next marker from the base class, which is one packet
        data = await super().read(len(self._marker))
        if not data:
            return data
        assert data == self._marker
        return self._packets.popleft()

    async def readexactly(self, _: int) -> bytes:
        raise NotImplementedError()


class UdpServerConnection(asyncio.DatagramProtocol, asyncio.StreamReaderProtocol):
    """Client-initiated UDP connection."""

    _server: UdpServer
    _client_addr: Address
    _server_addr: Address

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
            if server.is_transparent():
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
            self._server.datagram_received(data, (addr, self._server_addr))

    def connection_made(self, transport: asyncio.transports.DatagramTransport) -> None:
        # wrap the transport as writeable
        return super().connection_made(UdpWriteTransport(transport, self._client_addr))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        # remove the connection from the server
        del self._server._connections[(self._client_addr, self._server_addr) if self._server.is_transparent() else self._client_addr]
        return super().connection_lost(exc)

    def error_received(self, exc: Exception) -> None:
        # on error we're closing the connection
        self.connection_lost(exc)


class UdpWriteTransport(asyncio.WriteTransport):
    """Wrapper around a asyncio.DatagramTransport to support write via sendto."""

    # TODO forward other methods as well if supported

    _inner: asyncio.DatagramTransport
    _addr: Address

    def __init__(self, inner: asyncio.DatagramTransport, addr: Address):
        self._inner = inner
        self._addr = addr

    def get_extra_info(self, name: Any, default: Any = None) -> Any:
        return self._inner.get_extra_info(name, default)

    def is_closing(self) -> bool:
        self._inner.is_closing()

    def close(self) -> None:
        self._inner.close()

    def set_protocol(self, protocol: asyncio.BaseProtocol) -> None:
        self._inner.set_protocol(protocol)

    def get_protocol(self) -> asyncio.BaseProtocol:
        return self._inner.get_protocol()

    def write(self, data: Any) -> None:
        self._inner.sendto(data, self._addr)


class UdpOutgoingProtocol(asyncio.DatagramProtocol, asyncio.StreamReaderProtocol):
    """UDP protocol for server-initiated connections."""

    _filter_addr: Address

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
) -> asyncio.AbstractServer:
    """UDP variant of asyncio.start_server."""

    loop = asyncio.events.get_event_loop()
    family, addr = await _resolve_addr(loop, host, port)
    sock = socket.socket(family=family, type=socket.SocketKind.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if transparent:
            sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)
            sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
            sock.recvfrom = _recvfrom_transparent
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
        remote_addr=addr
    )
    writer = asyncio.StreamWriter(UdpWriteTransport(transport, addr), protocol, reader, loop)
    return reader, writer
