import pytest

from mitmproxy.net.udp import MAX_DATAGRAM_SIZE, DatagramReader


@pytest.mark.asyncio
async def test_reader():
    reader = DatagramReader()
    addr = ("8.8.8.8", 53)
    reader.feed_data(b"First message", addr)
    with pytest.raises(AssertionError):
        reader.feed_data(bytearray(MAX_DATAGRAM_SIZE + 1), addr)
    reader.feed_data(b"Second message", addr)
    reader.feed_eof()
    assert await reader.read(65535) == b"First message"
    with pytest.raises(AssertionError):
        await reader.read(MAX_DATAGRAM_SIZE - 1)
    assert await reader.read(65535) == b"Second message"
    assert not await reader.read(65535)
