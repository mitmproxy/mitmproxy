"""
Parsing for the PROXY protocol (v1 text and v2 binary), as specified by HAProxy:
https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt

Widely used by load balancers and other reverse proxies (AWS NLB, HAProxy, Envoy,
nginx, Traefik, ...) to preserve the original client address across a hop that would
otherwise replace it with their own.

When enabled via the `proxy_protocol` option, every new inbound connection is expected
to start with such a header before any real client traffic (HTTP, TLS, ...) follows.
"""

from __future__ import annotations

import ipaddress
import struct
from asyncio import IncompleteReadError
from asyncio import StreamReader
from dataclasses import dataclass

from mitmproxy.connection import Address

V2_SIGNATURE = b"\r\n\r\n\x00\r\nQUIT\n"
V1_PREFIX = b"PROXY "
_MAX_V1_LINE_LENGTH = 107  # per spec, including the trailing CRLF


class ProxyProtocolError(ValueError):
    """Raised when a PROXY protocol header is malformed or missing."""


@dataclass(frozen=True)
class ProxyHeader:
    """The addresses recovered from a PROXY protocol header."""

    source_addr: Address | None
    """The original client address, or None for `PROXY UNKNOWN`/LOCAL connections."""
    dest_addr: Address | None
    """The address the original client connected to, if provided."""


async def read_proxy_header(reader: StreamReader) -> ProxyHeader:
    """
    Read and consume a PROXY protocol header (v1 or v2) from `reader`.

    Raises `ProxyProtocolError` if the stream does not start with a well-formed header.
    """
    try:
        prefix = await reader.readexactly(len(V2_SIGNATURE))
    except IncompleteReadError as e:
        raise ProxyProtocolError(
            f"connection closed while reading PROXY protocol header: {e}"
        ) from e

    if prefix == V2_SIGNATURE:
        return await _read_v2_body(reader)
    else:
        return await _read_v1_line(reader, prefix)


async def _read_v1_line(reader: StreamReader, prefix: bytes) -> ProxyHeader:
    if not prefix.startswith(V1_PREFIX):
        raise ProxyProtocolError(f"not a PROXY protocol header: {prefix!r}")

    line = prefix
    while not line.endswith(b"\r\n"):
        if len(line) >= _MAX_V1_LINE_LENGTH:
            raise ProxyProtocolError("PROXY v1 header line too long")
        try:
            line += await reader.readexactly(1)
        except IncompleteReadError as e:
            raise ProxyProtocolError(
                f"connection closed while reading PROXY v1 header: {e}"
            ) from e

    return parse_v1(line)


def parse_v1(line: bytes) -> ProxyHeader:
    """Parse a single PROXY v1 header line (including the trailing CRLF)."""
    if not line.startswith(V1_PREFIX) or not line.endswith(b"\r\n"):
        raise ProxyProtocolError(f"malformed PROXY v1 header: {line!r}")

    fields = line[:-2].split(b" ")
    # fields[0] == b"PROXY"
    match fields[1:]:
        case [b"UNKNOWN", *_]:
            return ProxyHeader(source_addr=None, dest_addr=None)
        case [proto, src_ip, dst_ip, src_port, dst_port]:
            if proto not in (b"TCP4", b"TCP6"):
                raise ProxyProtocolError(f"unsupported PROXY v1 protocol: {proto!r}")
            try:
                source_addr = (src_ip.decode("ascii"), int(src_port))
                dest_addr = (dst_ip.decode("ascii"), int(dst_port))
            except (UnicodeDecodeError, ValueError) as e:
                raise ProxyProtocolError(
                    f"malformed PROXY v1 address in {line!r}: {e}"
                ) from e
            return ProxyHeader(source_addr=source_addr, dest_addr=dest_addr)
        case _:
            raise ProxyProtocolError(f"malformed PROXY v1 header: {line!r}")


async def _read_v2_body(reader: StreamReader) -> ProxyHeader:
    try:
        ver_cmd, fam_proto, body_len = struct.unpack(
            "!BBH", await reader.readexactly(4)
        )
        body = await reader.readexactly(body_len)
    except IncompleteReadError as e:
        raise ProxyProtocolError(
            f"connection closed while reading PROXY v2 header: {e}"
        ) from e

    version = ver_cmd >> 4
    command = ver_cmd & 0x0F
    if version != 2:
        raise ProxyProtocolError(f"unsupported PROXY protocol version: {version}")
    if command == 0x0:  # LOCAL: connection from the proxy itself (e.g. health check)
        return ProxyHeader(source_addr=None, dest_addr=None)
    if command != 0x1:  # PROXY
        raise ProxyProtocolError(f"unsupported PROXY v2 command: {command}")

    family = fam_proto >> 4
    return parse_v2_addresses(family, body)


def parse_v2_addresses(family: int, body: bytes) -> ProxyHeader:
    """Parse the address block of a PROXY v2 header (family nibble + body bytes)."""
    if family == 0x1:  # AF_INET
        fmt = "!4s4sHH"
    elif family == 0x2:  # AF_INET6
        fmt = "!16s16sHH"
    elif family == 0x0:  # AF_UNSPEC (e.g. UNKNOWN)
        return ProxyHeader(source_addr=None, dest_addr=None)
    else:
        raise ProxyProtocolError(f"unsupported PROXY v2 address family: {family}")

    size = struct.calcsize(fmt)
    if len(body) < size:
        raise ProxyProtocolError("PROXY v2 address block too short")
    src_raw, dst_raw, src_port, dst_port = struct.unpack(fmt, body[:size])

    src_ip = ipaddress.ip_address(src_raw).compressed
    dst_ip = ipaddress.ip_address(dst_raw).compressed
    return ProxyHeader(
        source_addr=(src_ip, src_port),
        dest_addr=(dst_ip, dst_port),
    )
