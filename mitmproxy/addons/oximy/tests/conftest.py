"""Shared pytest fixtures for Oximy addon tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# =============================================================================
# gRPC/Protobuf Fixtures
# =============================================================================

@pytest.fixture
def grpc_single_frame() -> bytes:
    """Single gRPC frame with 3-byte message 'abc'."""
    # Frame format: [1B compression] [4B length big-endian] [N bytes message]
    return b'\x00\x00\x00\x00\x03abc'


@pytest.fixture
def grpc_multi_frame() -> bytes:
    """Two gRPC frames."""
    frame1 = b'\x00\x00\x00\x00\x03abc'
    frame2 = b'\x00\x00\x00\x00\x03def'
    return frame1 + frame2


@pytest.fixture
def grpc_incomplete_frame() -> bytes:
    """Incomplete gRPC frame (header says 10 bytes, only 3 present)."""
    return b'\x00\x00\x00\x00\x0aabc'


# =============================================================================
# SSE (Server-Sent Events) Fixtures
# =============================================================================

@pytest.fixture
def sse_simple() -> bytes:
    """Simple SSE stream with data lines."""
    return b'data: {"message": "hello"}\n\ndata: {"message": "world"}\n\n'


@pytest.fixture
def sse_with_events() -> bytes:
    """SSE stream with event types."""
    return b'event: message\ndata: {"content": "test"}\n\nevent: done\ndata: [DONE]\n\n'


@pytest.fixture
def sse_with_comments() -> bytes:
    """SSE stream with comments (lines starting with :)."""
    return b': this is a comment\ndata: {"value": 42}\n\n'


@pytest.fixture
def sse_done_marker() -> bytes:
    """SSE with OpenAI-style [DONE] marker."""
    return b'data: {"delta": "text"}\n\ndata: [DONE]\n\n'


# =============================================================================
# Anti-Hijack Prefix Fixtures
# =============================================================================

@pytest.fixture
def anti_hijack_google() -> bytes:
    """Google-style anti-hijack prefix."""
    return b")]}'\n{\"data\": 123}"


@pytest.fixture
def anti_hijack_facebook() -> bytes:
    """Facebook-style anti-hijack prefix."""
    return b'for(;;);{"user": "test"}'


@pytest.fixture
def anti_hijack_while() -> bytes:
    """While-loop anti-hijack prefix."""
    return b'while(1);{"status": "ok"}'


@pytest.fixture
def anti_hijack_empty_obj() -> bytes:
    """Empty object anti-hijack prefix."""
    return b'{}&&{"result": true}'


@pytest.fixture
def anti_hijack_length_prefixed() -> bytes:
    """Length-prefixed streaming response after anti-hijack prefix."""
    return b")]}'\n15\n{\"chunk\": \"a\"}\n15\n{\"chunk\": \"b\"}\n"


# =============================================================================
# Encoding Fixtures
# =============================================================================

@pytest.fixture
def gzip_hello() -> bytes:
    """Gzip-compressed 'hello'."""
    import gzip
    return gzip.compress(b'hello')


@pytest.fixture
def base64_hello() -> bytes:
    """Base64-encoded 'hello world' (long enough to pass MIN_BASE64_LENGTH)."""
    import base64
    return base64.b64encode(b'hello world test data')


@pytest.fixture
def url_encoded() -> bytes:
    """URL percent-encoded string."""
    return b'hello%20world%21'


# =============================================================================
# Mock Process Fixtures
# =============================================================================

@pytest.fixture
def mock_psutil_process():
    """Mock psutil.Process object."""
    proc = MagicMock()
    proc.pid = 1234
    proc.ppid.return_value = 1
    proc.username.return_value = "testuser"
    proc.exe.return_value = "/Applications/Safari.app/Contents/MacOS/Safari"
    return proc


@pytest.fixture
def mock_psutil_connections():
    """Mock psutil network connections."""
    conn1 = MagicMock()
    conn1.laddr = MagicMock(port=54321)
    conn1.raddr = MagicMock(port=8080)
    conn1.pid = 1234

    conn2 = MagicMock()
    conn2.laddr = MagicMock(port=54322)
    conn2.raddr = None
    conn2.pid = 5678

    return [conn1, conn2]
