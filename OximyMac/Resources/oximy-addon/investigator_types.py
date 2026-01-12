"""
Type definitions for the Investigation Mode addon.

These types capture raw traffic data for analysis and debugging,
preserving information that the production addon normalizes away.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Literal

from process import ClientProcess


def _generate_uuid7() -> str:
    """Generate a UUID v7 (time-sortable)."""
    timestamp_ms = int(time.time() * 1000)
    timestamp_bytes = timestamp_ms.to_bytes(6, "big")
    rand_bytes = random.getrandbits(74)
    uuid_int = (
        (int.from_bytes(timestamp_bytes, "big") << 80)
        | (0x7 << 76)
        | ((rand_bytes >> 62) << 64)
        | (0x2 << 62)
        | (rand_bytes & ((1 << 62) - 1))
    )
    return str(uuid.UUID(int=uuid_int))


@dataclass
class SSEChunk:
    """
    A single SSE chunk from a streaming response.

    Preserves timing and raw data for debugging SSE parsing issues.
    """

    index: int  # Chunk number (0-based)
    timestamp: str  # ISO8601 when chunk arrived
    event_type: str | None  # SSE event field (if present)
    data_raw: str  # Raw data field content
    data_parsed: dict[str, Any] | None  # Attempted JSON parse (None if failed)
    delta_ms: int  # Milliseconds since previous chunk
    size_bytes: int  # Size of raw chunk

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data_raw": self.data_raw,
            "delta_ms": self.delta_ms,
            "size_bytes": self.size_bytes,
        }
        if self.event_type:
            result["event_type"] = self.event_type
        if self.data_parsed is not None:
            result["data_parsed"] = self.data_parsed
        return result


@dataclass
class ParseAttempt:
    """
    Records what the parser attempted and any errors encountered.

    Helps debug why parsing failed for a specific request/response.
    """

    api_format: str | None  # Format attempted (openai, anthropic, etc.)
    request_extracted: dict[str, Any] | None  # What was extracted from request
    response_extracted: dict[str, Any] | None  # What was extracted from response
    errors: list[str] = field(default_factory=list)  # Any errors during parsing

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.api_format:
            result["api_format"] = self.api_format
        if self.request_extracted:
            result["request_extracted"] = self.request_extracted
        if self.response_extracted:
            result["response_extracted"] = self.response_extracted
        if self.errors:
            result["errors"] = self.errors
        return result


@dataclass
class MatchAttempt:
    """
    Records how the traffic matcher classified this request.
    """

    classification: Literal["full_trace", "identifiable", "drop"]
    source_type: str | None  # api, app, website
    source_id: str | None  # openai, chatgpt, etc.
    api_format: str | None
    endpoint: str | None
    match_reason: str | None  # domain_lookup, domain_pattern, website, unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "api_format": self.api_format,
            "endpoint": self.endpoint,
            "match_reason": self.match_reason,
        }


@dataclass
class InvestigationEvent:
    """
    Raw traffic capture for investigation/debugging.

    Unlike OximyEvent which normalizes data, this preserves:
    - Raw request/response bodies
    - Individual SSE chunks with timing
    - Parse attempts and errors
    - Full headers
    """

    # Identity
    event_id: str
    timestamp: str

    # Connection info
    host: str
    url: str
    path: str
    method: str
    scheme: str  # http or https

    # Client attribution
    client: ClientProcess | None

    # Request data
    request_headers: dict[str, str]
    request_content_type: str | None
    request_body_raw: str | None  # Raw body as string (truncated if too large)
    request_body_parsed: dict[str, Any] | None  # Attempted JSON parse
    request_body_size: int
    request_body_truncated: bool  # True if body was truncated

    # Response data
    response_status: int
    response_headers: dict[str, str]
    response_content_type: str | None
    response_body_raw: str | None  # Raw body (for non-SSE)
    response_body_parsed: dict[str, Any] | None  # Attempted JSON parse
    response_body_size: int
    response_body_truncated: bool

    # SSE streaming data
    is_sse: bool
    sse_chunks: list[SSEChunk] | None  # Individual chunks if SSE
    sse_reconstructed_content: str | None  # What we reconstructed

    # Timing
    duration_ms: int | None
    ttfb_ms: int | None  # Time to first byte

    # Classification/parsing attempts
    match_attempt: MatchAttempt | None
    parse_attempt: ParseAttempt | None

    # Metadata
    flow_id: str  # mitmproxy flow ID for correlation
    session_id: str  # Investigation session ID
    tags: list[str] = field(default_factory=list)  # User-defined tags
    notes: str | None = None  # User notes

    @classmethod
    def create(
        cls,
        host: str,
        url: str,
        path: str,
        method: str,
        scheme: str,
        flow_id: str,
        session_id: str,
        **kwargs,
    ) -> InvestigationEvent:
        """Create a new investigation event with auto-generated ID and timestamp."""
        return cls(
            event_id=_generate_uuid7(),
            timestamp=datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            host=host,
            url=url,
            path=path,
            method=method,
            scheme=scheme,
            flow_id=flow_id,
            session_id=session_id,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        result: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "flow_id": self.flow_id,
            # Connection
            "connection": {
                "host": self.host,
                "url": self.url,
                "path": self.path,
                "method": self.method,
                "scheme": self.scheme,
            },
            # Timing
            "timing": {
                "duration_ms": self.duration_ms,
                "ttfb_ms": self.ttfb_ms,
            },
        }

        # Client
        if self.client:
            result["client"] = self.client.to_dict()

        # Request
        result["request"] = {
            "headers": self.request_headers,
            "content_type": self.request_content_type,
            "body_size": self.request_body_size,
            "body_truncated": self.request_body_truncated,
        }
        if self.request_body_raw is not None:
            result["request"]["body_raw"] = self.request_body_raw
        if self.request_body_parsed is not None:
            result["request"]["body_parsed"] = self.request_body_parsed

        # Response
        result["response"] = {
            "status": self.response_status,
            "headers": self.response_headers,
            "content_type": self.response_content_type,
            "body_size": self.response_body_size,
            "body_truncated": self.response_body_truncated,
        }
        if not self.is_sse:
            if self.response_body_raw is not None:
                result["response"]["body_raw"] = self.response_body_raw
            if self.response_body_parsed is not None:
                result["response"]["body_parsed"] = self.response_body_parsed

        # SSE
        result["sse"] = {
            "is_sse": self.is_sse,
        }
        if self.is_sse:
            if self.sse_chunks:
                result["sse"]["chunk_count"] = len(self.sse_chunks)
                result["sse"]["chunks"] = [c.to_dict() for c in self.sse_chunks]
            if self.sse_reconstructed_content:
                result["sse"]["reconstructed_content"] = self.sse_reconstructed_content

        # Classification
        if self.match_attempt:
            result["match_attempt"] = self.match_attempt.to_dict()

        # Parsing
        if self.parse_attempt:
            result["parse_attempt"] = self.parse_attempt.to_dict()

        # Tags/notes
        if self.tags:
            result["tags"] = self.tags
        if self.notes:
            result["notes"] = self.notes

        return result


@dataclass
class InvestigationSession:
    """
    Metadata about an investigation session.

    Written at the start of each session for context.
    """

    session_id: str
    started_at: str
    description: str | None
    filters: dict[str, Any]  # Active filters (domains, apps, etc.)

    @classmethod
    def create(
        cls, description: str | None = None, filters: dict[str, Any] | None = None
    ) -> InvestigationSession:
        return cls(
            session_id=_generate_uuid7(),
            started_at=datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            description=description,
            filters=filters or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "session_start",
            "session_id": self.session_id,
            "started_at": self.started_at,
            "description": self.description,
            "filters": self.filters,
        }
