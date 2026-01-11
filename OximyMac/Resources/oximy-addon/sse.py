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
                    # Skip non-JSON data like "v1" encoding marker
                    if data_str.strip() not in ("v1", "v2"):
                        logger.debug(f"Failed to parse SSE data: {data_str[:100]}")

    def _accumulate_data(self, data: dict[str, Any] | str) -> None:
        """Accumulate content from a parsed SSE data object."""
        # Handle case where data is a string (some APIs send raw strings)
        if isinstance(data, str):
            # Skip encoding markers
            if data.strip() in ("v1", "v2"):
                return
            self.accumulated_content += data
            return

        self.raw_chunks.append(data)

        # Try to extract model (usually in first chunk)
        if not self.model:
            self.model = data.get("model")
            # ChatGPT web format: model in metadata.model_slug
            if not self.model and data.get("type") == "server_ste_metadata":
                self.model = data.get("metadata", {}).get("model_slug")

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
        # ChatGPT web format: shorthand continuation - just {"v": "text"} with no p/o
        # This continues the previous append operation
        if "v" in data and "o" not in data and "p" not in data:
            value = data.get("v")
            if isinstance(value, str):
                return value

        # ChatGPT web format: delta patches with "o": "append" and path to content
        # Example: {"p": "/message/content/parts/0", "o": "append", "v": "hello"}
        if data.get("o") == "append" and "v" in data:
            path = data.get("p", "")
            value = data.get("v")
            if isinstance(value, str) and self._is_content_path(path):
                return value

        # ChatGPT web format: patch array with nested operations
        # Example: {"o": "patch", "v": [{"p": "/message/content/parts/0", "o": "append", "v": "text"}]}
        if data.get("o") == "patch" and isinstance(data.get("v"), list):
            content_parts = []
            for patch in data["v"]:
                if patch.get("o") == "append":
                    path = patch.get("p", "")
                    value = patch.get("v")
                    if isinstance(value, str) and self._is_content_path(path):
                        content_parts.append(value)
            if content_parts:
                return "".join(content_parts)

        # OpenAI API format: choices[0].delta.content
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

    def _is_content_path(self, path: str) -> bool:
        """Check if a JSON patch path is for message content."""
        # Match paths like:
        # - /message/content/parts/0
        # - /content/parts/0
        # - /parts/0
        # - /text
        # Avoid paths like /status, /metadata, /create_time
        if not path:
            return False
        content_indicators = ("/content", "/parts", "/text")
        exclude_indicators = ("/status", "/metadata", "/create_time", "/id", "/author")
        return any(ind in path for ind in content_indicators) and not any(ind in path for ind in exclude_indicators)

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

        logger.debug(f"SSE finalized: content={self.accumulated_content!r} chunks={len(self.raw_chunks)}")

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

    Mitmproxy calls the stream handler with each chunk of data (bytes).
    The handler should return bytes or an iterable of bytes.

    Args:
        buffer: SSEBuffer to accumulate data

    Returns:
        Stream handler function that processes each chunk
    """

    def handler(data: bytes) -> bytes:
        # Process the chunk to accumulate SSE data
        buffer.process_chunk(data)
        # Pass through unchanged
        return data

    return handler
