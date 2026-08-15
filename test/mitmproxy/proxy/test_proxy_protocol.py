import asyncio

import pytest

from mitmproxy.proxy.proxy_protocol import parse_v1
from mitmproxy.proxy.proxy_protocol import parse_v2_addresses
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


async def test_immediate_close():
    """A health-check style probe that opens and closes without sending anything."""
    reader = await _reader_for(b"")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


def test_parse_v1_rejects_line_without_proxy_prefix():
    with pytest.raises(ProxyProtocolError):
        parse_v1(b"GET / HTTP/1.1\r\n")


async def test_v1_wrong_field_count():
    reader = await _reader_for(b"PROXY TCP4 1.2.3.4 5.6.7.8\r\n")
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v2_truncated_body():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",
            0x21,  # version 2, command PROXY
            0x11,  # family AF_INET, protocol STREAM
            0x00,
            0x0C,  # length = 12, but we only send 5 body bytes below
        ]
    )
    reader = await _reader_for(header_bytes + bytes(5))
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v2_unsupported_command():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",
            0x22,  # version 2, command 2 (unassigned)
            0x11,
            0x00,
            0x00,
        ]
    )
    reader = await _reader_for(header_bytes)
    with pytest.raises(ProxyProtocolError):
        await read_proxy_header(reader)


async def test_v2_tcp6():
    header_bytes = bytes(
        [
            *b"\r\n\r\n\x00\r\nQUIT\n",
            0x21,  # version 2, command PROXY
            0x21,  # family AF_INET6, protocol STREAM
            0x00,
            0x24,  # length = 36 (16 + 16 + 2 + 2)
            *([0] * 15 + [1]),  # src ::1
            *([0] * 15 + [2]),  # dst ::2
            0x00,
            0x01,  # src port 1
            0x00,
            0x02,  # dst port 2
        ]
    )
    reader = await _reader_for(header_bytes)
    header = await read_proxy_header(reader)
    assert header.source_addr == ("::1", 1)
    assert header.dest_addr == ("::2", 2)


def test_parse_v2_addresses_unspec_family():
    header = parse_v2_addresses(0x0, b"")
    assert header.source_addr is None
    assert header.dest_addr is None


def test_parse_v2_addresses_unsupported_family():
    with pytest.raises(ProxyProtocolError):
        parse_v2_addresses(0x3, b"")  # AF_UNIX, not supported


def test_parse_v2_addresses_body_too_short():
    with pytest.raises(ProxyProtocolError):
        parse_v2_addresses(0x1, bytes(4))  # AF_INET needs 12 bytes
