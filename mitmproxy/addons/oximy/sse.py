"""
Server-Sent Events (SSE) streaming response handler.

Accumulates SSE chunks to reconstruct the full response content
for streaming AI API responses.

Also handles Gemini's custom length-prefixed streaming format.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from mitmproxy.addons.oximy.parser import parse_gemini_response, parse_grok_response

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
        # Standard SSE uses double newline to separate events
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            self._process_event(event)

        # ChatGPT uses single newline between delta/message events
        # Process any complete lines in the remaining buffer
        while "\n" in self._buffer:
            line, rest = self._buffer.split("\n", 1)
            line = line.strip()
            # Check if this looks like a complete ChatGPT event
            if line.startswith(("delta ", "message ", "data: ")):
                self._process_event(line)
                self._buffer = rest
            else:
                # Not a complete event, wait for more data
                break

    def _process_event(self, event: str) -> None:
        """Process a single SSE event."""
        lines = event.strip().split("\n")

        for line in lines:
            data_str = None
            event_type = None

            # Standard SSE format: data: {...}
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                event_type = "data"
            # ChatGPT format: delta {...} or message {...}
            elif line.startswith("delta "):
                data_str = line[6:]  # Remove "delta " prefix
                event_type = "delta"
            elif line.startswith("message "):
                data_str = line[8:]  # Remove "message " prefix
                event_type = "message"
            # Skip encoding markers and other non-data lines
            elif line.strip() in ("delta_encoding v1", "delta_encoding v2", "v1", "v2", ""):
                continue
            else:
                continue

            if data_str is None:
                continue

            # Check for stream end signals
            if data_str.strip() in ("[DONE]", ""):
                logger.debug(f"SSE stream end signal: {data_str}")
                continue

            try:
                data = json.loads(data_str)
                self._accumulate_data(data)
            except json.JSONDecodeError:
                # Skip non-JSON data like "v1" encoding marker
                if data_str.strip() not in ("v1", "v2"):
                    logger.debug(f"Failed to parse SSE {event_type} data: {data_str[:100]}")

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
            # Log significant content additions (every 500 chars or first 100)
            total_len = len(self.accumulated_content)
            if total_len <= 100 or total_len % 500 < len(content_delta):
                logger.debug(f"SSE content: +{len(content_delta)} chars = {total_len} total")

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
        # ChatGPT/DeepSeek shorthand: {"v": "text"} - simple string value
        if "v" in data and isinstance(data.get("v"), str):
            # Skip if this is a non-content operation with a path
            if "p" in data and not self._is_content_path(data.get("p", "")):
                return None
            return data["v"]

        # ChatGPT patch array: {"o": "patch", "v": [{...}, {...}]}
        if data.get("o") == "patch" and isinstance(data.get("v"), list):
            content_parts = []
            for patch in data["v"]:
                value = patch.get("v")
                path = patch.get("p", "")
                if isinstance(value, str) and self._is_content_path(path):
                    content_parts.append(value)
            if content_parts:
                return "".join(content_parts)

        # DeepSeek BATCH format
        if data.get("o") == "BATCH" and isinstance(data.get("v"), list):
            content_parts = []
            for op in data["v"]:
                if op.get("p") == "fragments" and isinstance(op.get("v"), list):
                    for frag in op["v"]:
                        if isinstance(frag, dict) and "content" in frag:
                            content_parts.append(frag["content"])
            if content_parts:
                return "".join(content_parts)

        # OpenAI API format: choices[0].delta.content
        choices = data.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            if "content" in delta:
                return delta["content"]

        # Anthropic format: delta.text
        if data.get("type") == "content_block_delta":
            return data.get("delta", {}).get("text")

        return None

    def _is_content_path(self, path: str) -> bool:
        """Check if a JSON patch path is for message content."""
        if not path:
            return True  # No path means it's a shorthand continuation
        # Match paths like /message/content/parts/0, /content/parts/0, /text
        # Exclude paths like /status, /metadata, /create_time
        content_indicators = ("/content", "/parts", "/text")
        exclude_indicators = ("/status", "/metadata", "/create_time", "/id", "/author")
        return any(ind in path for ind in content_indicators) and not any(ind in path for ind in exclude_indicators)

    def _extract_finish_reason(self, data: dict[str, Any]) -> str | None:
        """Extract finish reason from SSE chunk."""
        # DeepSeek format: BATCH with status FINISHED
        # {"p":"response","o":"BATCH","v":[{"p":"status","v":"FINISHED"},...]}
        if data.get("o") == "BATCH" and isinstance(data.get("v"), list):
            for op in data["v"]:
                if op.get("p") == "status" and op.get("v") == "FINISHED":
                    return "stop"

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

        # Log warning if content looks truncated (ends mid-word or mid-entity)
        if self.accumulated_content:
            if self.accumulated_content.rstrip().endswith(('["', '["turn', '\ue200entity\ue202["', '- **')):
                logger.warning(f"SSE content appears truncated: ends with '{self.accumulated_content[-50:]}'")

        logger.info(f"SSE finalized: content_len={len(self.accumulated_content)} chunks={len(self.raw_chunks)} model={self.model}")

        return {
            "content": self.accumulated_content,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
        }


@dataclass
class GeminiBuffer:
    """
    Accumulates Gemini streaming response data.

    Gemini uses a custom length-prefixed format, not SSE:
    )]}'\n
    <length>\n
    <json_chunk>\n
    ...

    This buffer accumulates all raw bytes and parses them at the end.
    """

    accumulated_bytes: bytes = b""

    def process_chunk(self, chunk: bytes) -> bytes:
        """
        Accumulate a chunk from the Gemini response stream.

        Args:
            chunk: Raw bytes from the response stream

        Returns:
            The original chunk (pass-through)
        """
        if not chunk:
            # Empty chunk signals end of stream
            logger.info(f"GeminiBuffer.process_chunk: END OF STREAM, total accumulated: {len(self.accumulated_bytes)} bytes")
            return chunk

        self.accumulated_bytes += chunk
        # Log first 100 chars of chunk content for debugging
        try:
            preview = chunk.decode('utf-8')[:100].replace('\n', '\\n')
        except UnicodeDecodeError:
            preview = f"<binary: {chunk[:50]}>"
        logger.info(f"GeminiBuffer.process_chunk: +{len(chunk)} bytes = {len(self.accumulated_bytes)} total. Preview: {preview}")
        return chunk

    def finalize(self) -> dict[str, Any]:
        """
        Finalize the buffer and parse the accumulated response.

        Returns:
            Dict with content, model, conversation_id, response_id
        """
        logger.info(f"GeminiBuffer.finalize: parsing {len(self.accumulated_bytes)} bytes")

        if not self.accumulated_bytes:
            logger.info("GeminiBuffer.finalize: no bytes accumulated!")
            return {"content": None, "model": "gemini"}

        # Log first 500 chars of accumulated data for debugging
        try:
            preview = self.accumulated_bytes.decode('utf-8')[:500].replace('\n', '\\n')
        except UnicodeDecodeError:
            preview = f"<binary data>"
        logger.info(f"GeminiBuffer.finalize: data preview: {preview}")

        result = parse_gemini_response(self.accumulated_bytes)
        content_len = len(result.get('content') or '')
        logger.info(f"GeminiBuffer.finalize: parsed content length = {content_len}")
        if content_len > 0:
            logger.info(f"GeminiBuffer.finalize: content preview: {result.get('content')[:200]}")
        return result


def is_gemini_streaming_response(flow) -> bool:
    """
    Check if a flow is a Gemini streaming response.

    Args:
        flow: mitmproxy HTTPFlow

    Returns:
        True if this is a Gemini streaming response
    """
    if not flow.request:
        return False

    host = flow.request.pretty_host.lower()
    path = flow.request.path.lower()

    # Gemini streaming endpoint
    is_gemini = "gemini.google.com" in host
    has_stream = "streamgenerate" in path

    if is_gemini:
        logger.info(f"is_gemini_streaming_response: host={host}, path={path[:100]}, has_stream={has_stream}")

    return is_gemini and has_stream


def create_gemini_stream_handler(buffer: GeminiBuffer):
    """
    Create a stream handler function for Gemini responses.

    Args:
        buffer: GeminiBuffer to accumulate data

    Returns:
        Stream handler function that processes each chunk
    """

    def handler(data: bytes) -> bytes:
        # Accumulate the chunk
        buffer.process_chunk(data)
        # Pass through unchanged
        return data

    return handler


@dataclass
class GrokBuffer:
    """
    Accumulates Grok streaming response data.

    Grok uses concatenated JSON objects (not SSE, not length-prefixed):
    {"result":{"response":{"token":"Yo",...}}}{"result":{"response":{"token":" yo",...}}}...

    This buffer accumulates all raw bytes and parses them at the end.
    """

    accumulated_bytes: bytes = b""

    def process_chunk(self, chunk: bytes) -> bytes:
        """
        Accumulate a chunk from the Grok response stream.

        Args:
            chunk: Raw bytes from the response stream

        Returns:
            The original chunk (pass-through)
        """
        if not chunk:
            logger.info(f"GrokBuffer.process_chunk: END OF STREAM, total accumulated: {len(self.accumulated_bytes)} bytes")
            return chunk

        self.accumulated_bytes += chunk
        try:
            preview = chunk.decode('utf-8')[:100].replace('\n', '\\n')
        except UnicodeDecodeError:
            preview = f"<binary: {chunk[:50]}>"
        logger.info(f"GrokBuffer.process_chunk: +{len(chunk)} bytes = {len(self.accumulated_bytes)} total. Preview: {preview}")
        return chunk

    def finalize(self) -> dict[str, Any]:
        """
        Finalize the buffer and parse the accumulated response.

        Returns:
            Dict with content, model, conversation_id, response_id
        """
        logger.info(f"GrokBuffer.finalize: parsing {len(self.accumulated_bytes)} bytes")

        if not self.accumulated_bytes:
            logger.info("GrokBuffer.finalize: no bytes accumulated!")
            return {"content": None, "model": None}

        # Log first 500 chars of accumulated data for debugging
        try:
            preview = self.accumulated_bytes.decode('utf-8')[:500].replace('\n', '\\n')
        except UnicodeDecodeError:
            preview = "<binary data>"
        logger.info(f"GrokBuffer.finalize: data preview: {preview}")

        result = parse_grok_response(self.accumulated_bytes)
        content_len = len(result.get('content') or '')
        logger.info(f"GrokBuffer.finalize: parsed content length = {content_len}")
        if content_len > 0:
            logger.info(f"GrokBuffer.finalize: content preview: {result.get('content')[:200]}")
        return result


def is_grok_streaming_response(flow) -> bool:
    """
    Check if a flow is a Grok streaming response.

    Args:
        flow: mitmproxy HTTPFlow

    Returns:
        True if this is a Grok chat streaming response
    """
    if not flow.request:
        return False

    host = flow.request.pretty_host.lower()
    path = flow.request.path.lower()
    method = flow.request.method

    # Grok chat endpoints
    is_grok = "grok.com" in host
    is_chat = "/rest/app-chat/conversations" in path and (
        path.endswith("/new") or "/responses" in path
    )

    result = is_grok and is_chat and method == "POST"

    if is_grok:
        logger.info(f"is_grok_streaming_response: host={host}, path={path[:100]}, method={method}, is_chat={is_chat}, result={result}")

    return result


def create_grok_stream_handler(buffer: GrokBuffer):
    """
    Create a stream handler function for Grok responses.

    Args:
        buffer: GrokBuffer to accumulate data

    Returns:
        Stream handler function that processes each chunk
    """

    def handler(data: bytes) -> bytes:
        buffer.process_chunk(data)
        return data

    return handler


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
    chunk_count = [0]  # Use list to allow mutation in closure

    def handler(data: bytes) -> bytes:
        chunk_count[0] += 1
        # Process the chunk to accumulate SSE data
        buffer.process_chunk(data)

        # Log progress periodically
        if chunk_count[0] % 20 == 0:
            logger.debug(f"SSE chunk #{chunk_count[0]}: accumulated {len(buffer.accumulated_content)} chars")

        if not data:
            logger.info(f"SSE stream ended after {chunk_count[0]} chunks, total content: {len(buffer.accumulated_content)} chars")

        # Pass through unchanged
        return data

    return handler
