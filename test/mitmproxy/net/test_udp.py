import asyncio
import pytest

from mitmproxy.net.udp import MAX_UDP_PACKET_SIZE, UdpStreamReader


@pytest.mark.asyncio
async def test_reader():
    reader = UdpStreamReader(asyncio.get_event_loop())
    reader.feed_data(b'First message')
    with pytest.raises(ValueError):
        reader.feed_data(bytearray(MAX_UDP_PACKET_SIZE + 1))
    reader.feed_data(b'')
    reader.feed_data(b'Second message')
    reader.feed_eof()
    with pytest.raises(NotImplementedError):
        await reader.readline()
    with pytest.raises(NotImplementedError):
        await reader.readuntil()
    with pytest.raises(NotImplementedError):
        await reader.readexactly(0)
    assert await reader.read(65535) == b'First message'
    with pytest.raises(ValueError):
        await reader.read(MAX_UDP_PACKET_SIZE - 1)
    assert await reader.read(65535) == b'Second message'
    assert not await reader.read(65535)
