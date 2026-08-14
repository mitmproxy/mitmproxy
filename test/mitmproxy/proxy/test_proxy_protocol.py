import asyncio

import pytest

from mitmproxy.proxy.proxy_protocol import ProxyProtocolError
from mitmproxy.proxy.proxy_protocol import read_proxy_header


async def _reader_for(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


async def test_v1_tcp4():
    reader = await _reader_for(
        b"PROXY TCP4 192.168.0.1 192.168.0.11 56324 443\r\nGET / HTTP/1.1\r\n"
    )
    header = await read_proxy_header(reader)
    assert header.source_addr == ("192.168.0.1", 56324)
    assert header.dest_addr == ("192.168.0.11", 443)
    # the header line is consumed, the remaining traffic is untouched.
    assert await reader.readline() == b"GET / HTTP/1.1\r\n"


async def test_v1_tcp6():
    reader = await _reader_for(b"PROXY TCP6 ::1 ::2 1 2\r\n")
    header = await read_proxy_header(reader)
    assert header.source_addr == ("::1", 1)
    assert header.dest_addr == ("::2", 2)


async def test_v1_unknown():
    reader = await _reader_for(b"PROXY UNKNOWN\r\nGET / HTTP/1.1\r\n")
    header = await read_proxy_header(reader)
    assert header.source_addr is None
    assert header.dest_addr is None


async def test_v1_malformed():
    reader = await _reader_for(b"PROXY BOGUS 1.2.3.4 5.6.7.8 1 2\r\n")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v1_bad_port():
    reader = await _reader_for(b"PROXY TCP4 1.2.3.4 5.6.7.8 notaport 2\r\n")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v1_line_too_long():
    reader = await _reader_for(b"PROXY " + b"A" * 200 + b"\r\n")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_not_proxy_protocol():
    reader = await _reader_for(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_truncated_connection():
    reader = await _reader_for(b"PROXY TCP4 1.2.3")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v2_tcp4():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",  # signature
            0x21,  # version 2, command PROXY
            0x11,  # family AF_INET, protocol STREAM
            0x00,
            0x0C,  # length = 12
            192,
            168,
            0,
            1,  # src addr
            192,
            168,
            0,
            11,  # dst addr
            0xDB,
            0x14,  # src port 56340... actually just arbitrary bytes below
            0x01,
            0xBB,  # dst port 443
        ]
    )
    reader = await _reader_for(header_bytes + b"remaining-tcp-payload")
    header = await read_proxy_header(reader)
    assert header.source_addr == ("192.168.0.1", 0xDB14)
    assert header.dest_addr == ("192.168.0.11", 443)
    assert await reader.read() == b"remaining-tcp-payload"


async def test_v2_local_command():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",
            0x20,  # version 2, command LOCAL
            0x00,
            0x00,
            0x00,  # length = 0
        ]
    )
    reader = await _reader_for(header_bytes)
    header = await read_proxy_header(reader)
    assert header.source_addr is None
    assert header.dest_addr is None


async def test_v2_unsupported_version():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",
            0x11,  # version 1 (unsupported), command PROXY
            0x11,
            0x00,
            0x00,
        ]
    )
    reader = await _reader_for(header_bytes)
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)
