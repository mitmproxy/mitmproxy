import asyncio
from typing import Optional
import pytest
from mitmproxy.connection import Address
from mitmproxy.net.udp import MAX_DATAGRAM_SIZE, DatagramReader, DatagramWriter, open_connection, start_server
from mitmproxy.test import taddons


async def test_client_server():
    server_reader = DatagramReader()
    server_writer: Optional[DatagramWriter] = None

    def handle_datagram(
        transport: asyncio.DatagramTransport,
        data: bytes,
        remote_addr: Address,
        local_addr: Address
    ):
        nonlocal server_reader, server_writer
        if server_writer is None:
            server_writer = DatagramWriter(transport, remote_addr, server_reader)
        server_reader.feed_data(data, remote_addr)

    server = await start_server(handle_datagram, "127.0.0.1", 0)
    assert repr(server).startswith("<UdpServer socket=")

    [client_reader, client_writer] = await open_connection(*server.sockets[0].getsockname())
    assert client_writer.get_extra_info("peername") == server.sockets[0].getsockname()
    assert client_writer.get_extra_info("sockname") == client_writer._protocol.sockets[0].getsockname()

    client_writer.write(b"msg1")
    client_writer.write(b"msg2")
    client_writer.write(b"msg3")
    with pytest.raises(OSError):
        client_writer.write_eof()

    assert await server_reader.read(MAX_DATAGRAM_SIZE) == b"msg1"
    assert await server_reader.read(MAX_DATAGRAM_SIZE) == b"msg2"
    assert await server_reader.read(MAX_DATAGRAM_SIZE) == b"msg3"

    assert server_writer is not None
    server.pause_writing()
    server_writer.write(b"msg4")
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(server_writer.drain(), 2)
    server.resume_writing()
    await server.drain()

    assert await client_reader.read(MAX_DATAGRAM_SIZE) == b"msg4"
    client_writer.close()
    await client_writer.wait_closed()

    server_writer.close()
    await server_writer.wait_closed()

    server.close()
    await server.wait_closed()


async def test_reader():
    with taddons.context() as tctx:
        reader = DatagramReader()
        addr = ("8.8.8.8", 53)
        reader.feed_data(b"First message", addr)
        with pytest.raises(AssertionError):
            reader.feed_data(bytearray(MAX_DATAGRAM_SIZE + 1), addr)
        reader.feed_data(b"Second message", addr)
        reader.feed_eof()
        reader.feed_data(b"too late", ("1.2.3.4", 5))
        await tctx.master.await_log("Received UDP packet from 1.2.3.4:5 after EOF")
        assert await reader.read(65535) == b"First message"
        with pytest.raises(AssertionError):
            await reader.read(MAX_DATAGRAM_SIZE - 1)
        assert await reader.read(65535) == b"Second message"
        assert not await reader.read(65535)
        assert not await reader.read(65535)
        full_reader = DatagramReader()
        for i in range(0, 42):
            full_reader.feed_data(bytes([i]), addr)
        full_reader.feed_data(b"too much", ("1.2.3.4", 5))
        await tctx.master.await_log("Dropped UDP packet from 1.2.3.4:5")
        full_reader.feed_eof()