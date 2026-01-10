"""
Core type definitions for the Oximy addon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TYPE_CHECKING
import uuid
import time
import random

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.process import ClientProcess


@dataclass
class MatchResult:
    """Result of matching a flow against the OISP bundle."""

    classification: Literal["full_trace", "identifiable", "drop"]
    source_type: Literal["api", "app", "website"] | None = None
    source_id: str | None = None  # "openai", "cursor", "chatgpt"
    provider_id: str | None = None  # "openai", "anthropic"
    api_format: str | None = None  # "openai", "anthropic", "google"
    endpoint: str | None = None  # "chat", "voice", etc.


@dataclass
class EventSource:
    """Source information for an event."""

    type: Literal["api", "app", "website"]
    id: str
    endpoint: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "endpoint": self.endpoint,
        }


@dataclass
class InteractionRequest:
    """Parsed request data."""

    messages: list[dict] | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict] | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        result: dict = {}
        if self.messages is not None:
            result["messages"] = self.messages
        if self.model is not None:
            result["model"] = self.model
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.tools is not None:
            result["tools"] = self.tools
        if self.raw is not None:
            result["_raw"] = self.raw
        return result


@dataclass
class InteractionResponse:
    """Parsed response data."""

    content: str | None = None
    model: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
    raw: dict | None = None

    def to_dict(self) -> dict:
        result: dict = {}
        if self.content is not None:
            result["content"] = self.content
        if self.model is not None:
            result["model"] = self.model
        if self.finish_reason is not None:
            result["finish_reason"] = self.finish_reason
        if self.usage is not None:
            result["usage"] = self.usage
        if self.raw is not None:
            result["_raw"] = self.raw
        return result


@dataclass
class Interaction:
    """Full interaction data for full_trace events."""

    model: str | None
    request: InteractionRequest
    response: InteractionResponse

    def to_dict(self) -> dict:
        result: dict = {
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
        }
        if self.model is not None:
            result["model"] = self.model
        return result


@dataclass
class EventTiming:
    """Timing information for an event."""

    duration_ms: int | None = None
    ttfb_ms: int | None = None

    def to_dict(self) -> dict:
        result: dict = {}
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.ttfb_ms is not None:
            result["ttfb_ms"] = self.ttfb_ms
        return result


@dataclass
class OximyEvent:
    """
    An OISP event representing an AI interaction.

    This is the normalized format written to JSONL files.
    """

    event_id: str
    timestamp: str
    source: EventSource
    trace_level: Literal["full", "identifiable"]
    timing: EventTiming
    interaction: Interaction | None = None
    metadata: dict | None = None
    client: ClientProcess | None = None

    @classmethod
    def create(
        cls,
        source: EventSource,
        trace_level: Literal["full", "identifiable"],
        timing: EventTiming,
        interaction: Interaction | None = None,
        metadata: dict | None = None,
        client: ClientProcess | None = None,
    ) -> OximyEvent:
        """Create a new event with auto-generated ID and timestamp."""
        event_id = _generate_uuid7()
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        return cls(
            event_id=event_id,
            timestamp=timestamp,
            source=source,
            trace_level=trace_level,
            timing=timing,
            interaction=interaction,
            metadata=metadata,
            client=client,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        result = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source.to_dict(),
            "trace_level": self.trace_level,
            "timing": self.timing.to_dict(),
        }

        if self.client:
            result["client"] = self.client.to_dict()

        if self.trace_level == "full" and self.interaction:
            result["interaction"] = self.interaction.to_dict()
        elif self.trace_level == "identifiable" and self.metadata:
            result["metadata"] = self.metadata

        return result


def _generate_uuid7() -> str:
    """Generate a UUID v7 (time-sortable) or fall back to v4."""
    # UUID v7: timestamp (48 bits) + version (4 bits) + random (12 bits) + variant (2 bits) + random (62 bits)
    timestamp_ms = int(time.time() * 1000)
    timestamp_bytes = timestamp_ms.to_bytes(6, "big")

    # Random bytes for the rest
    rand_bytes = random.getrandbits(74)

    # Construct UUID v7
    uuid_int = (
        (int.from_bytes(timestamp_bytes, "big") << 80)
        | (0x7 << 76)  # version 7
        | ((rand_bytes >> 62) << 64)
        | (0x2 << 62)  # variant
        | (rand_bytes & ((1 << 62) - 1))
    )

    return str(uuid.UUID(int=uuid_int))


@dataclass
class DomainPattern:
    """A compiled regex pattern for matching dynamic domains."""

    pattern: str
    compiled: object  # re.Pattern
    provider_id: str
