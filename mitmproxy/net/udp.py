from __future__ import annotations

import asyncio
import ipaddress
import socket
import struct
from typing import Any, Callable, Optional, Union, cast
from mitmproxy import ctx
from mitmproxy.connection import Address
from mitmproxy.utils import human


MAX_DATAGRAM_SIZE = 65535 - 20

DatagramReceivedCallback = Callable[
    [asyncio.DatagramTransport, bytes, Address, Address], None
]
"""
Callable that gets invoked when a datagram is received.
The first argument is the outgoing transport.
The second argument is the received payload.
The third argument is the source address, also referred to as `remote_addr` or `peername`.
The fourth argument is the destination address, also referred to as `local_addr` or `sockname`.
In the case of transparent server, the last argument is the original destination address.
"""

# to make mypy happy
SockAddress = Union[tuple[str, int], tuple[str, int, int, int]]


class TransparentSocket(socket.socket):
    SOL_IP = getattr(socket, "SOL_IP", 0)
    IP_TRANSPARENT = getattr(socket, "IP_TRANSPARENT", 19)
    IP_RECVORIGDSTADDR = getattr(socket, "IP_RECVORIGDSTADDR", 20)

    def __init__(self, family: socket.AddressFamily, local_addr: SockAddress) -> None:
        self._recvmsg = getattr(self, "recvmsg")
        if not self._recvmsg:
            raise NotImplementedError(
                "Transparent UDP sockets are only supporting on platforms providing recvmsg."
            )
        super().__init__(
            family=family, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
        )
        try:
            self.setblocking(False)
            self.setsockopt(
                TransparentSocket.SOL_IP, TransparentSocket.IP_TRANSPARENT, 1
            )
            self.setsockopt(
                TransparentSocket.SOL_IP, TransparentSocket.IP_RECVORIGDSTADDR, 1
            )
            self.bind(local_addr)
        except:
            self.close()
            raise

    @staticmethod
    def _unpack_addr(sockaddr_in: bytes) -> SockAddress:
        """Converts a native sockaddr into a python tuple."""

        (family,) = struct.unpack_from("h", sockaddr_in, 0)
        if family == socket.AF_INET:
            port, in4_addr, _ = struct.unpack_from("!H4s8s", sockaddr_in, 2)
            return str(ipaddress.IPv4Address(in4_addr)), port
        elif family == socket.AF_INET6:
            port, flowinfo, in6_addr, scopeid = struct.unpack_from(
                "!HL16sL", sockaddr_in, 2
            )
            return str(ipaddress.IPv6Address(in6_addr)), port, flowinfo, scopeid
        else:
            raise NotImplementedError(f"family {family} not implemented")

    def recvfrom(
        self, bufsize: int, flags: int = 0
    ) -> tuple[bytes, tuple[SockAddress, SockAddress]]:
        """Same as recvfrom, but always returns source and destination addresses."""

        data, ancdata, _, client_addr = self._recvmsg(
            bufsize, socket.CMSG_SPACE(1024), flags
        )
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if (
                cmsg_level == TransparentSocket.SOL_IP
                and cmsg_type == TransparentSocket.IP_RECVORIGDSTADDR
            ):
                server_addr = TransparentSocket._unpack_addr(cmsg_data)
                break
        else:
            raise OSError("recvmsg did not return th original destination address")
        return data, (client_addr, server_addr)


class DrainableDatagramProtocol(asyncio.DatagramProtocol):

    _loop: asyncio.AbstractEventLoop
    _closed: asyncio.Event
    _paused: int
    _can_write: asyncio.Event
    _sock: socket.socket | None

    def __init__(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = asyncio.get_running_loop() if loop is None else loop
        self._closed = asyncio.Event()
        self._paused = 0
        self._can_write = asyncio.Event()
        self._can_write.set()
        self._sock = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} socket={self._sock!r}>"

    @property
    def sockets(self) -> tuple[socket.socket, ...]:
        return () if self._sock is None else (self._sock,)

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._sock = transport.get_extra_info("socket")

    def connection_lost(self, exc: Exception | None) -> None:
        self._closed.set()
        if exc:
            ctx.log.warn(f"Connection lost on {self!r}: {exc!r}")

    def pause_writing(self) -> None:
        self._paused = self._paused + 1
        if self._paused == 1:
            self._can_write.clear()

    def resume_writing(self) -> None:
        assert self._paused > 0
        self._paused = self._paused - 1
        if self._paused == 0:
            self._can_write.set()

    async def drain(self) -> None:
        await self._can_write.wait()

    def error_received(self, exc: Exception) -> None:
        ctx.log.warn(f"Send/receive on {self!r} failed: {exc!r}")

    async def wait_closed(self) -> None:
        await self._closed.wait()


class UdpServer(DrainableDatagramProtocol):
    """UDP server similar to base_events.Server"""

    # _datagram_received_cb: DatagramReceivedCallback
    _transport: asyncio.DatagramTransport | None
    _transparent_transports: dict[Address, asyncio.DatagramTransport] | None
    _local_addr: Address | None

    def __init__(
        self,
        datagram_received_cb: DatagramReceivedCallback,
        loop: asyncio.AbstractEventLoop | None,
        transparent: bool,
    ) -> None:
        super().__init__(loop)
        self._datagram_received_cb = datagram_received_cb
        self._transport = None
        self._transparent_transports = {} if transparent else None
        self._local_addr = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if self._transport is None:
            self._transport = cast(asyncio.DatagramTransport, transport)
            self._local_addr = transport.get_extra_info("sockname")
            super().connection_made(transport)

    async def _datagram_received_for_new_transparent_addr(
        self, data: bytes, remote_addr: Address, local_addr: Address
    ) -> None:
        assert self._sock is not None
        assert self._transparent_transports is not None
        sock = socket.socket(
            family=self._sock.family, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
        )
        try:
            sock.setblocking(False)
            sock.setsockopt(
                TransparentSocket.SOL_IP, TransparentSocket.IP_TRANSPARENT, 1
            )
            sock.shutdown(socket.SHUT_RD)
            sock.bind(local_addr)
        except:
            sock.close()
            raise
        transport, _ = await self._loop.create_datagram_endpoint(
            lambda: self, sock=sock
        )
        self._transparent_transports[local_addr] = cast(
            asyncio.DatagramTransport, transport
        )
        self._datagram_received_cb(
            self._transparent_transports[local_addr], data, remote_addr, local_addr
        )

    def datagram_received(self, data: bytes, addr: Any) -> None:
        assert self._transport is not None
        if self._transparent_transports is None:
            assert self._local_addr is not None
            self._datagram_received_cb(self._transport, data, addr, self._local_addr)
        else:
            remote_addr, local_addr = addr
            if local_addr in self._transparent_transports:
                self._datagram_received_cb(
                    self._transparent_transports[local_addr],
                    data,
                    remote_addr,
                    local_addr,
                )
            else:
                self._loop.create_task(
                    self._datagram_received_for_new_transparent_addr(
                        data, remote_addr, local_addr
                    )
                )

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
        if self._transparent_transports is not None:
            for transport in self._transparent_transports.values():
                transport.close()


class DatagramReader:

    _packets: asyncio.Queue
    _eof: bool

    def __init__(self) -> None:
        self._packets = asyncio.Queue(42)  # ~2.75MB
        self._eof = False

    def feed_data(self, data: bytes, remote_addr: Address) -> None:
        assert len(data) <= MAX_DATAGRAM_SIZE
        if self._eof:
            ctx.log.info(
                f"Received UDP packet from {human.format_address(remote_addr)} after EOF."
            )
        else:
            try:
                self._packets.put_nowait(data)
            except asyncio.QueueFull:
                ctx.log.debug(
                    f"Dropped UDP packet from {human.format_address(remote_addr)}."
                )

    def feed_eof(self) -> None:
        self._eof = True
        try:
            self._packets.put_nowait(b"")
        except asyncio.QueueFull:
            pass

    async def read(self, n: int) -> bytes:
        assert n >= MAX_DATAGRAM_SIZE
        if self._eof:
            try:
                return self._packets.get_nowait()
            except asyncio.QueueEmpty:
                return b""
        else:
            return await self._packets.get()


class DatagramWriter:

    _transport: asyncio.DatagramTransport
    _remote_addr: Address
    _reader: DatagramReader | None
    _closed: asyncio.Event | None

    def __init__(
        self,
        transport: asyncio.DatagramTransport,
        remote_addr: Address,
        reader: DatagramReader | None = None,
    ) -> None:
        """
        Create a new datagram writer around the given transport.
        Specify a reader to prevent closing the transport and instead only feed EOF to the reader.
        """
        self._transport = transport
        self._remote_addr = remote_addr
        proto = transport.get_protocol()
        assert isinstance(proto, DrainableDatagramProtocol)
        self._reader = reader
        self._closed = asyncio.Event() if reader is not None else None

    @property
    def _protocol(self) -> DrainableDatagramProtocol:
        return cast(DrainableDatagramProtocol, self._transport.get_protocol())

    def write(self, data: bytes) -> None:
        self._transport.sendto(data, self._remote_addr)

    def write_eof(self) -> None:
        raise NotImplementedError("UDP does not support half-closing.")

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        if name == "peername":
            return self._remote_addr
        else:
            return self._transport.get_extra_info(name, default)

    def close(self) -> None:
        if self._closed is None:
            self._transport.close()
        else:
            self._closed.set()
        if self._reader is not None:
            self._reader.feed_eof()

    async def wait_closed(self) -> None:
        if self._closed is None:
            await self._protocol.wait_closed()
        else:
            await self._closed.wait()

    async def drain(self) -> None:
        await self._protocol.drain()


class UdpClient(DrainableDatagramProtocol):
    """UDP protocol for upstream connections."""

    _reader: DatagramReader

    def __init__(self, reader: DatagramReader, loop: asyncio.AbstractEventLoop | None):
        super().__init__(loop)
        self._reader = reader

    def datagram_received(self, data: bytes, remote_addr: Address) -> None:
        self._reader.feed_data(data, remote_addr)

    def connection_lost(self, exc: Exception | None) -> None:
        self._reader.feed_eof()
        super().connection_lost(exc)


async def start_server(
    datagram_received_cb: DatagramReceivedCallback,
    host: str,
    port: int,
    *,
    transparent: bool = False,
) -> UdpServer:
    """UDP variant of asyncio.start_server."""

    loop = asyncio.get_running_loop()

    if transparent:
        addrinfos = await loop.getaddrinfo(host, port)
        exception = OSError(f"getaddrinfo for host '{host}' failed")
        for family, _, _, _, addr in addrinfos:
            try:
                sock = TransparentSocket(family=family, local_addr=addr)
            except OSError as exc:
                exception = exc
            else:
                break
        else:
            raise exception
    else:
        sock = None

    _, protocol = await loop.create_datagram_endpoint(
        lambda: UdpServer(datagram_received_cb, loop, transparent),
        local_addr=(host, port),
        sock=sock,
    )
    assert isinstance(protocol, UdpServer)
    return protocol


async def open_connection(
    host: str, port: int, *, local_addr: Optional[Address] = None
) -> tuple[DatagramReader, DatagramWriter]:
    """UDP variant of asyncio.open_connection."""

    loop = asyncio.get_running_loop()
    reader = DatagramReader()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: UdpClient(reader, loop), local_addr=local_addr, remote_addr=(host, port)
    )
    writer = DatagramWriter(
        cast(asyncio.DatagramTransport, transport),
        remote_addr=transport.get_extra_info("peername"),
    )
    return reader, writer
