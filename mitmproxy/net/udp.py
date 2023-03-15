from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Callable, Optional, Union, cast

from mitmproxy.connection import Address
from mitmproxy.net import udp_wireguard
from mitmproxy.utils import human

logger = logging.getLogger(__name__)

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
"""

# to make mypy happy
SockAddress = Union[tuple[str, int], tuple[str, int, int, int]]


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
            logger.warning(f"Connection lost on {self!r}: {exc!r}")  # pragma: no cover

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
        logger.warning(f"Send/receive on {self!r} failed: {exc!r}")  # pragma: no cover

    async def wait_closed(self) -> None:
        await self._closed.wait()


class UdpServer(DrainableDatagramProtocol):
    """UDP server similar to base_events.Server"""

    # _datagram_received_cb: DatagramReceivedCallback
    _transport: asyncio.DatagramTransport | None
    _local_addr: Address | None

    def __init__(
        self,
        datagram_received_cb: DatagramReceivedCallback,
        loop: asyncio.AbstractEventLoop | None,
    ) -> None:
        super().__init__(loop)
        self._datagram_received_cb = datagram_received_cb
        self._transport = None
        self._local_addr = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if self._transport is None:
            self._transport = cast(asyncio.DatagramTransport, transport)
            self._transport.set_protocol(self)
            self._local_addr = transport.get_extra_info("sockname")
            super().connection_made(transport)

    def datagram_received(self, data: bytes, addr: Any) -> None:
        assert self._transport is not None
        assert self._local_addr is not None
        self._datagram_received_cb(self._transport, data, addr, self._local_addr)

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()


class DatagramReader:
    _packets: asyncio.Queue
    _eof: bool

    def __init__(self) -> None:
        self._packets = asyncio.Queue(42)  # ~2.75MB
        self._eof = False

    def feed_data(self, data: bytes, remote_addr: Address) -> None:
        assert len(data) <= MAX_DATAGRAM_SIZE
        if self._eof:
            logger.info(
                f"Received UDP packet from {human.format_address(remote_addr)} after EOF."
            )
        else:
            try:
                self._packets.put_nowait(data)
            except asyncio.QueueFull:
                logger.debug(
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
            try:
                return await self._packets.get()
            except RuntimeError:  # pragma: no cover
                # event loop got closed
                return b""


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
        if reader is not None:
            self._reader = reader
            self._closed = asyncio.Event()
        else:
            self._reader = None
            self._closed = None

    @property
    def _protocol(self) -> DrainableDatagramProtocol | udp_wireguard.WireGuardDatagramTransport:
        return self._transport.get_protocol()  # type: ignore

    def write(self, data: bytes) -> None:
        self._transport.sendto(data, self._remote_addr)

    def write_eof(self) -> None:
        raise OSError("UDP does not support half-closing.")

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
            assert self._reader
            self._reader.feed_eof()

    def is_closing(self) -> bool:
        if self._closed is None:
            return self._transport.is_closing()
        else:
            return self._closed.is_set()

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
) -> UdpServer:
    """UDP variant of asyncio.start_server."""

    if host == "":
        # binding to an empty string does not work on Windows or Ubuntu.
        host = "0.0.0.0"

    loop = asyncio.get_running_loop()
    _, protocol = await loop.create_datagram_endpoint(
        lambda: UdpServer(datagram_received_cb, loop),
        local_addr=(host, port),
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
