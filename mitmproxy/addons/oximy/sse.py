"""
Server-Sent Events (SSE) streaming response handler.

DEPRECATED: This module contains legacy code that has been replaced by
the data-driven ConfigurableStreamBuffer in parser.py.

All buffer classes and helper functions are commented out.
Use ConfigurableStreamBuffer with websites.json configuration instead.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# DEPRECATED LEGACY CODE - COMMENTED OUT
# Use ConfigurableStreamBuffer from parser.py instead
# =============================================================================

# @dataclass
# class SSEBuffer:
#     """
#     DEPRECATED: Use ConfigurableStreamBuffer with format="sse" instead.
#
#     Accumulates SSE stream data for a single response.
#     """
#     api_format: str | None = None
#     accumulated_content: str = ""
#     model: str | None = None
#     finish_reason: str | None = None
#     usage: dict[str, Any] | None = None
#     raw_chunks: list[dict[str, Any]] = field(default_factory=list)
#     _buffer: str = ""
#
#     def process_chunk(self, chunk: bytes) -> bytes: ...
#     def finalize(self) -> dict[str, Any]: ...


# @dataclass
# class GeminiBuffer:
#     """
#     DEPRECATED: Use ConfigurableStreamBuffer with format="length_prefixed" instead.
#
#     Accumulates Gemini streaming response data.
#     """
#     accumulated_bytes: bytes = b""
#
#     def process_chunk(self, chunk: bytes) -> bytes: ...
#     def finalize(self) -> dict[str, Any]: ...


# @dataclass
# class GrokBuffer:
#     """
#     DEPRECATED: Use ConfigurableStreamBuffer with format="ndjson" instead.
#
#     Accumulates Grok streaming response data.
#     """
#     accumulated_bytes: bytes = b""
#
#     def process_chunk(self, chunk: bytes) -> bytes: ...
#     def finalize(self) -> dict[str, Any]: ...


# =============================================================================
# Stub classes for backward compatibility during migration
# These raise errors to ensure we're using the data-driven approach
# =============================================================================

class SSEBuffer:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        raise NotImplementedError(
            "SSEBuffer is deprecated. Use ConfigurableStreamBuffer from parser.py "
            "with format='sse' and configuration from websites.json"
        )


class GeminiBuffer:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        raise NotImplementedError(
            "GeminiBuffer is deprecated. Use ConfigurableStreamBuffer from parser.py "
            "with format='length_prefixed' and configuration from websites.json"
        )


class GrokBuffer:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        raise NotImplementedError(
            "GrokBuffer is deprecated. Use ConfigurableStreamBuffer from parser.py "
            "with format='ndjson' and configuration from websites.json"
        )


# =============================================================================
# Helper functions - these can still be used but matching should be data-driven
# =============================================================================

def is_sse_response(headers: dict[str, str] | Any) -> bool:
    """
    Check if response headers indicate an SSE stream.

    Args:
        headers: Response headers (dict or mitmproxy Headers object)

    Returns:
        True if content-type indicates SSE
    """
    content_type = ""

    if hasattr(headers, "get"):
        content_type = headers.get("content-type", "")

    return "text/event-stream" in content_type.lower()


def is_gemini_streaming_response(flow: Any) -> bool:
    """
    DEPRECATED: Matching should be done via websites.json patterns.

    Check if a flow is a Gemini streaming response.
    """
    if not flow.request:
        return False

    host = flow.request.pretty_host.lower()
    path = flow.request.path.lower()

    is_gemini = "gemini.google.com" in host
    has_stream = "streamgenerate" in path

    return is_gemini and has_stream


def is_grok_streaming_response(flow: Any) -> bool:
    """
    DEPRECATED: Matching should be done via websites.json patterns.

    Check if a flow is a Grok streaming response.
    """
    if not flow.request:
        return False

    host = flow.request.pretty_host.lower()
    path = flow.request.path.lower()
    method = flow.request.method

    is_grok = "grok.com" in host
    is_chat = "/rest/app-chat/conversations" in path and (
        path.endswith("/new") or "/responses" in path
    )

    return is_grok and is_chat and method == "POST"


def create_sse_stream_handler(buffer: Any) -> Any:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""
    raise NotImplementedError(
        "create_sse_stream_handler is deprecated. Use ConfigurableStreamBuffer "
        "from parser.py with format='sse'"
    )


def create_gemini_stream_handler(buffer: Any) -> Any:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""
    raise NotImplementedError(
        "create_gemini_stream_handler is deprecated. Use ConfigurableStreamBuffer "
        "from parser.py with format='length_prefixed'"
    )


def create_grok_stream_handler(buffer: Any) -> Any:
    """DEPRECATED: Use ConfigurableStreamBuffer from parser.py instead."""
    raise NotImplementedError(
        "create_grok_stream_handler is deprecated. Use ConfigurableStreamBuffer "
        "from parser.py with format='ndjson'"
    )
