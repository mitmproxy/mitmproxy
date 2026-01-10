"""
Server-Sent Events (SSE) streaming response handler.

Accumulates SSE chunks to reconstruct the full response content
for streaming AI API responses.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SSEBuffer:
    """
    Accumulates SSE stream data for a single response.

    Handles the common SSE format used by AI APIs:
    - OpenAI: data: {...}\n\n with delta.content
    - Anthropic: data: {...}\n\n with delta.text
    """

    api_format: str | None = None
    accumulated_content: str = ""
    model: str | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    raw_chunks: list[dict[str, Any]] = field(default_factory=list)
    _buffer: str = ""

    def process_chunk(self, chunk: bytes) -> bytes:
        """
        Process an SSE chunk and accumulate data.

        This can be used as a streaming transformer - it processes
        the data while passing it through unchanged.

        Args:
            chunk: Raw bytes from the response stream

        Returns:
            The original chunk (pass-through)
        """
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return chunk

        self._buffer += text
        self._process_buffer()

        return chunk

    def _process_buffer(self) -> None:
        """Process complete SSE events from the buffer."""
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            self._process_event(event)

    def _process_event(self, event: str) -> None:
        """Process a single SSE event."""
        lines = event.strip().split("\n")

        for line in lines:
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix

                # Check for stream end signals
                if data_str.strip() in ("[DONE]", ""):
                    continue

                try:
                    data = json.loads(data_str)
                    self._accumulate_data(data)
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse SSE data: {data_str[:100]}")

    def _accumulate_data(self, data: dict[str, Any]) -> None:
        """Accumulate content from a parsed SSE data object."""
        self.raw_chunks.append(data)

        # Try to extract model (usually in first chunk)
        if not self.model:
            self.model = data.get("model")

        # Extract content based on API format
        content_delta = self._extract_content_delta(data)
        if content_delta:
            self.accumulated_content += content_delta

        # Extract finish reason (usually in last chunk)
        finish_reason = self._extract_finish_reason(data)
        if finish_reason:
            self.finish_reason = finish_reason

        # Extract usage (usually in last chunk)
        usage = data.get("usage")
        if usage:
            self.usage = usage

    def _extract_content_delta(self, data: dict[str, Any]) -> str | None:
        """Extract content delta from SSE chunk based on API format."""
        # OpenAI format: choices[0].delta.content
        choices = data.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                return content

        # Anthropic format: delta.text or content_block_delta
        delta = data.get("delta", {})
        if "text" in delta:
            return delta["text"]

        # Anthropic content_block_delta
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            return delta.get("text")

        return None

    def _extract_finish_reason(self, data: dict[str, Any]) -> str | None:
        """Extract finish reason from SSE chunk."""
        # OpenAI format
        choices = data.get("choices", [])
        if choices:
            reason = choices[0].get("finish_reason")
            if reason:
                return reason

        # Anthropic format
        if data.get("type") == "message_delta":
            delta = data.get("delta", {})
            return delta.get("stop_reason")

        # Direct stop_reason
        return data.get("stop_reason")

    def finalize(self) -> dict[str, Any]:
        """
        Finalize the buffer and return accumulated data.

        Returns:
            Dict with content, model, finish_reason, usage
        """
        # Process any remaining buffer
        if self._buffer.strip():
            self._process_event(self._buffer)
            self._buffer = ""

        return {
            "content": self.accumulated_content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
        }


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


def create_sse_stream_handler(buffer: SSEBuffer):
    """
    Create a stream handler function for mitmproxy.

    The returned function can be assigned to flow.response.stream
    to intercept and accumulate SSE data while passing it through.

    Args:
        buffer: SSEBuffer to accumulate data

    Returns:
        Stream handler function
    """

    def handler(chunks):
        for chunk in chunks:
            buffer.process_chunk(chunk)
            yield chunk

    return handler
