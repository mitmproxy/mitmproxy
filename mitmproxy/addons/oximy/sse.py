"""
Server-Sent Events (SSE) streaming response handler.

NOTE: The streaming buffer implementations have been moved to
ConfigurableStreamBuffer in parser.py which uses data-driven
configuration from websites.json and apps.json.

This module only contains utility functions for detecting stream types.
"""

from __future__ import annotations

from typing import Any


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
