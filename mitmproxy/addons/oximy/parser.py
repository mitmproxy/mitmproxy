"""
Request/Response parsing using JSONPath and JSONata extraction.

Extracts structured data (messages, model, usage, etc.) from
AI API requests and responses based on OISP parser configurations.

Supports:
- Standard JSON APIs (OpenAI, Anthropic, etc.)
- Form-encoded requests (Gemini)
- Custom JSON structures (DeepSeek)
- Data-driven stream parsing with ConfigurableStreamBuffer
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import parse_qs

try:
    import jsonata
    JSONATA_AVAILABLE = True
except ImportError:
    JSONATA_AVAILABLE = False
    jsonata = None

from mitmproxy.addons.oximy.types import InteractionRequest, InteractionResponse

logger = logging.getLogger(__name__)


class JSONPathExtractor:
    """
    Simple JSONPath extractor for common patterns.

    Supports:
    - $.field - Top level field
    - $.field.nested - Nested fields
    - $.field[0] - Array index
    - $.field[0].nested - Array index with nested field
    - $.field[*].nested - All array elements (returns list)
    """

    @staticmethod
    def extract(data: Any, path: str) -> Any:
        """
        Extract value from data using JSONPath-like syntax.

        Args:
            data: The JSON data (dict or list)
            path: JSONPath expression starting with $

        Returns:
            Extracted value, or None if not found
        """
        if not path or not path.startswith("$"):
            return None

        # Remove leading $
        path = path[1:]
        if path.startswith("."):
            path = path[1:]

        if not path:
            return data

        return JSONPathExtractor._extract_path(data, path)

    @staticmethod
    def _extract_path(data: Any, path: str) -> Any:
        """Recursively extract path components."""
        if data is None or not path:
            return data

        # Parse next path component
        # Match: field, field[0], field[*], [0], [*]
        match = re.match(r"^([^\.\[\]]+)?(?:\[(\d+|\*)\])?(?:\.(.*))?$", path)
        if not match:
            return None

        field, index, rest = match.groups()

        current = data

        # Navigate to field if specified
        if field:
            if not isinstance(current, dict):
                return None
            current = current.get(field)
            if current is None:
                return None

        # Handle array index
        if index is not None:
            if not isinstance(current, list):
                return None

            if index == "*":
                # Extract from all elements
                if rest:
                    return [
                        JSONPathExtractor._extract_path(item, rest)
                        for item in current
                        if JSONPathExtractor._extract_path(item, rest) is not None
                    ]
                return current
            else:
                # Specific index
                idx = int(index)
                if idx >= len(current):
                    return None
                current = current[idx]

        # Continue with rest of path
        if rest:
            return JSONPathExtractor._extract_path(current, rest)

        return current


class RequestParser:
    """Parses AI API requests based on OISP parser configurations."""

    def __init__(self, parsers: dict[str, dict[str, Any]]):
        """
        Args:
            parsers: OISP parsers config (api_format -> {request: {...}, response: {...}})
        """
        self.parsers = parsers

    def parse(
        self,
        body: bytes,
        api_format: str | None,
        include_raw: bool = True,
    ) -> InteractionRequest:
        """
        Parse request body using the appropriate parser config.

        Args:
            body: Raw request body bytes
            api_format: The API format (openai, anthropic, etc.)
            include_raw: Whether to include raw body in result

        Returns:
            Parsed InteractionRequest
        """
        # Try to parse JSON
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Failed to parse request body as JSON")
            return InteractionRequest(raw=None)

        # Handle ChatGPT web format specially
        if api_format and api_format.endswith("_web"):
            return self._parse_chatgpt_web(data, include_raw)

        # Get parser config
        parser_config = self._get_request_config(api_format)

        # Extract fields
        result = InteractionRequest(
            messages=self._extract(data, parser_config.get("messages")),
            model=self._extract(data, parser_config.get("model")),
            temperature=self._extract(data, parser_config.get("temperature")),
            max_tokens=self._extract(data, parser_config.get("max_tokens")),
            tools=self._extract(data, parser_config.get("tools")),
            raw=data if include_raw else None,
        )

        return result

    def _parse_chatgpt_web(self, data: dict[str, Any], include_raw: bool) -> InteractionRequest:
        """Parse ChatGPT web format request."""
        # ChatGPT web format:
        # {
        #   "action": "next",
        #   "messages": [{"author": {"role": "user"}, "content": {"parts": ["text"]}}],
        #   "model": "gpt-5-2",
        #   ...
        # }
        messages = None
        raw_messages = data.get("messages", [])
        if raw_messages:
            messages = []
            for msg in raw_messages:
                author = msg.get("author", {})
                role = author.get("role", "user")
                content = msg.get("content", {})
                # Extract text from parts
                parts = content.get("parts", [])
                text = "".join(str(p) for p in parts if isinstance(p, str))
                messages.append({
                    "role": role,
                    "content": text,
                })

        return InteractionRequest(
            messages=messages,
            model=data.get("model"),
            temperature=None,
            max_tokens=None,
            tools=None,
            raw=data if include_raw else None,
        )

    def _get_request_config(self, api_format: str | None) -> dict[str, str]:
        """Get request parser config for api_format."""
        if not api_format:
            return {}
        parser = self.parsers.get(api_format, {})
        return parser.get("request", {})

    def _extract(self, data: Any, path: str | None) -> Any:
        """Extract value using JSONPath."""
        if not path:
            return None
        return JSONPathExtractor.extract(data, path)


class ResponseParser:
    """Parses AI API responses based on OISP parser configurations."""

    def __init__(self, parsers: dict[str, dict[str, Any]]):
        """
        Args:
            parsers: OISP parsers config (api_format -> {request: {...}, response: {...}})
        """
        self.parsers = parsers

    def parse(
        self,
        body: bytes,
        api_format: str | None,
        include_raw: bool = True,
    ) -> InteractionResponse:
        """
        Parse response body using the appropriate parser config.

        Args:
            body: Raw response body bytes
            api_format: The API format (openai, anthropic, etc.)
            include_raw: Whether to include raw body in result

        Returns:
            Parsed InteractionResponse
        """
        # Try to parse JSON
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Failed to parse response body as JSON")
            return InteractionResponse(raw=None)

        # Get parser config
        parser_config = self._get_response_config(api_format)

        # Extract fields
        content = self._extract(data, parser_config.get("content"))

        # Handle Anthropic-style content (array of content blocks)
        if isinstance(content, list):
            # Try to extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "".join(text_parts) if text_parts else str(content)

        # Extract usage
        usage = self._extract(data, parser_config.get("usage"))
        if isinstance(usage, dict):
            # Normalize usage keys
            usage = self._normalize_usage(usage, parser_config)

        result = InteractionResponse(
            content=content if isinstance(content, str) else str(content) if content else None,
            model=self._extract(data, parser_config.get("model")),
            finish_reason=self._extract(data, parser_config.get("finish_reason"))
            or self._extract(data, parser_config.get("stop_reason")),
            usage=usage,
            raw=data if include_raw else None,
        )

        return result

    def _get_response_config(self, api_format: str | None) -> dict[str, Any]:
        """Get response parser config for api_format."""
        if not api_format:
            return {}
        parser = self.parsers.get(api_format, {})
        return parser.get("response", {})

    def _extract(self, data: Any, path: str | dict | None) -> Any:
        """Extract value using JSONPath or nested config."""
        if not path:
            return None
        if isinstance(path, str):
            return JSONPathExtractor.extract(data, path)
        if isinstance(path, dict):
            # Nested extraction config (like usage)
            result = {}
            for key, subpath in path.items():
                if isinstance(subpath, str):
                    value = JSONPathExtractor.extract(data, subpath)
                    if value is not None:
                        result[key] = value
            return result if result else None
        return None

    def _normalize_usage(self, usage: dict, config: dict) -> dict:
        """Normalize usage dict to standard keys."""
        # config could be used for provider-specific mappings in the future
        _ = config

        normalized: dict[str, Any] = {}

        # Map various key names to standard names
        key_mappings = [
            ("input_tokens", ["input_tokens", "prompt_tokens"]),
            ("output_tokens", ["output_tokens", "completion_tokens"]),
            ("total_tokens", ["total_tokens"]),
            ("cache_read_tokens", ["cache_read_input_tokens"]),
            ("cache_creation_tokens", ["cache_creation_input_tokens"]),
        ]

        for standard_key, possible_keys in key_mappings:
            for key in possible_keys:
                if key in usage:
                    normalized[standard_key] = usage[key]
                    break

        # Also keep any other keys that might be provider-specific
        for key, value in usage.items():
            if key not in normalized and value is not None:
                # Check if this is already mapped
                already_mapped = any(key in pk for _, pk in key_mappings if key in normalized)
                if not already_mapped:
                    normalized[key] = value

        return normalized


def parse_gemini_request(body: bytes) -> dict:
    """
    Parse Gemini request body.

    Gemini uses form-encoded requests with an `f.req` parameter containing
    a JSON array structure like: [null, "[[\"prompt text\",...], ...]"]

    Args:
        body: Raw request body bytes

    Returns:
        Dict with extracted prompt and metadata
    """
    result = {
        "prompt": None,
        "conversation_id": None,
        "response_id": None,
        "language": None,
    }

    try:
        decoded = body.decode("utf-8")
        params = parse_qs(decoded)

        f_req = params.get("f.req", [None])[0]
        if not f_req:
            return result

        # The f.req value is a JSON array where [1] contains the actual data
        outer = json.loads(f_req)
        if not isinstance(outer, list) or len(outer) < 2:
            return result

        # The second element is a JSON string that needs to be parsed again
        inner_json = outer[1]
        if not isinstance(inner_json, str):
            return result

        inner = json.loads(inner_json)
        if not isinstance(inner, list):
            return result

        # Extract prompt from [0][0]
        if len(inner) > 0 and isinstance(inner[0], list) and len(inner[0]) > 0:
            result["prompt"] = inner[0][0]

        # Extract language from [1][0] if available
        if len(inner) > 1 and isinstance(inner[1], list) and len(inner[1]) > 0:
            result["language"] = inner[1][0]

        # Extract conversation IDs from [2] if available
        if len(inner) > 2 and isinstance(inner[2], list):
            ids = inner[2]
            if len(ids) > 0 and isinstance(ids[0], str):
                result["conversation_id"] = ids[0]
            if len(ids) > 1 and isinstance(ids[1], str):
                result["response_id"] = ids[1]

    except (json.JSONDecodeError, UnicodeDecodeError, IndexError, TypeError) as e:
        logger.debug(f"Failed to parse Gemini request: {e}")

    return result


def parse_gemini_response(body: bytes) -> dict:
    """
    Parse Gemini streaming response body.

    Gemini response format:
    )]}'\\n
    <length>\\n
    <json_chunk>\\n
    ...

    Each JSON chunk is: [[\"wrb.fr\", null, \"<nested_json_string>\"]]
    The nested JSON contains the response text at [4][0][1][0].

    Args:
        body: Raw response body bytes

    Returns:
        Dict with extracted content and metadata
    """
    result = {
        "content": None,
        "model": "gemini",
        "conversation_id": None,
        "response_id": None,
    }

    try:
        decoded = body.decode("utf-8")
        logger.info(f"parse_gemini_response: raw body length={len(decoded)}, first 200 chars: {decoded[:200]}")

        # Remove the )]}' prefix if present
        if decoded.startswith(")]}'"):
            decoded = decoded[4:]
        decoded = decoded.strip()

        if not decoded:
            logger.info("parse_gemini_response: decoded is empty after strip")
            return result

        # Parse length-prefixed chunks and get the last one with content
        chunks = _parse_gemini_chunks(decoded)
        logger.info(f"parse_gemini_response: found {len(chunks)} chunks")

        for i, chunk_data in enumerate(reversed(chunks)):
            logger.info(f"parse_gemini_response: chunk {i} length={len(chunk_data)}, first 100 chars: {chunk_data[:100]}")
            parsed = _extract_gemini_content(chunk_data)
            if parsed.get("content"):
                result.update(parsed)
                logger.info(f"parse_gemini_response: found content in chunk {i}")
                break

    except (UnicodeDecodeError, IndexError, TypeError) as e:
        logger.debug(f"Failed to parse Gemini response: {e}")

    return result


def _parse_gemini_chunks(data: str) -> list[str]:
    """Parse length-prefixed chunks from Gemini response."""
    chunks = []
    pos = 0

    while pos < len(data):
        # Skip whitespace
        while pos < len(data) and data[pos] in " \n\r\t":
            pos += 1

        if pos >= len(data):
            break

        # Read length (digits until newline)
        length_start = pos
        while pos < len(data) and data[pos].isdigit():
            pos += 1

        if pos == length_start:
            pos += 1
            continue

        try:
            chunk_length = int(data[length_start:pos])
        except ValueError:
            pos += 1
            continue

        # Skip newline after length
        if pos < len(data) and data[pos] == "\n":
            pos += 1

        # Read chunk data
        if pos + chunk_length <= len(data):
            chunk = data[pos:pos + chunk_length]
            chunks.append(chunk)
            pos += chunk_length
        else:
            chunks.append(data[pos:])
            break

    return chunks


def _extract_gemini_content(chunk: str) -> dict:
    """Extract content from a single Gemini response chunk."""
    result = {
        "content": None,
        "conversation_id": None,
        "response_id": None,
    }

    try:
        outer = json.loads(chunk)
        if not isinstance(outer, list) or len(outer) == 0:
            return result

        # First element is typically ["wrb.fr", null, "<json_string>"]
        first = outer[0]
        if not isinstance(first, list) or len(first) < 3:
            return result

        inner_json = first[2]
        if not isinstance(inner_json, str):
            return result

        inner = json.loads(inner_json)
        if not isinstance(inner, list):
            return result

        # Extract conversation/response IDs from [1]
        if len(inner) > 1 and isinstance(inner[1], list):
            ids = inner[1]
            if len(ids) > 0:
                result["conversation_id"] = ids[0]
            if len(ids) > 1:
                result["response_id"] = ids[1]

        # Extract content from [4][0][1][0]
        if len(inner) > 4 and isinstance(inner[4], list):
            responses = inner[4]
            if len(responses) > 0 and isinstance(responses[0], list):
                response_data = responses[0]
                if len(response_data) > 1 and isinstance(response_data[1], list):
                    content_array = response_data[1]
                    if len(content_array) > 0:
                        result["content"] = content_array[0]

    except (json.JSONDecodeError, IndexError, TypeError) as e:
        logger.debug(f"Failed to extract Gemini content: {e}")

    return result


def parse_deepseek_request(body: bytes) -> dict:
    """
    Parse DeepSeek request body.

    DeepSeek uses simple JSON with a `prompt` field.

    Args:
        body: Raw request body bytes

    Returns:
        Dict with extracted prompt and metadata
    """
    result = {
        "prompt": None,
        "chat_session_id": None,
    }

    try:
        data = json.loads(body.decode("utf-8"))
        result["prompt"] = data.get("prompt")
        result["chat_session_id"] = data.get("chat_session_id")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.debug(f"Failed to parse DeepSeek request: {e}")

    return result


def parse_perplexity_request(body: bytes) -> dict:
    """
    Parse Perplexity AI request body.

    Perplexity uses JSON with query_str field and params object.

    Args:
        body: Raw request body bytes

    Returns:
        Dict with extracted prompt and metadata
    """
    result = {
        "prompt": None,
        "model": None,
        "search_focus": None,
    }

    try:
        data = json.loads(body.decode("utf-8"))
        result["prompt"] = data.get("query_str")
        params = data.get("params", {})
        result["model"] = params.get("model_preference")
        result["search_focus"] = params.get("search_focus")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.debug(f"Failed to parse Perplexity request: {e}")

    return result


def parse_grok_request(body: bytes) -> dict:
    """
    Parse Grok (xAI) request body.

    Grok uses JSON with message field and modelName.

    Args:
        body: Raw request body bytes

    Returns:
        Dict with extracted prompt and metadata
    """
    result = {
        "prompt": None,
        "model": None,
        "conversation_id": None,
    }

    try:
        data = json.loads(body.decode("utf-8"))
        result["prompt"] = data.get("message")
        result["model"] = data.get("modelName")
        # responseMetadata may contain additional model info
        response_meta = data.get("responseMetadata", {})
        request_model = response_meta.get("requestModelDetails", {})
        if request_model.get("modelId"):
            result["model"] = request_model.get("modelId")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.debug(f"Failed to parse Grok request: {e}")

    return result


def parse_grok_response(body: bytes) -> dict:
    """
    Parse Grok (xAI) streaming response body.

    Grok uses newline-delimited JSON objects where tokens are in
    result.response.token and the final message is in
    result.response.modelResponse.message.

    Args:
        body: Raw response body bytes

    Returns:
        Dict with extracted content and metadata
    """
    result = {
        "content": None,
        "model": None,
        "conversation_id": None,
        "response_id": None,
    }

    try:
        decoded = body.decode("utf-8")

        # Parse newline-delimited JSON objects
        accumulated_tokens = []
        final_message = None

        for line in decoded.strip().split("}{"):
            # Reconstruct JSON objects that were split
            if not line.startswith("{"):
                line = "{" + line
            if not line.endswith("}"):
                line = line + "}"

            try:
                data = json.loads(line)
                response = data.get("result", {}).get("response", {})

                # Accumulate tokens
                token = response.get("token")
                if token:
                    accumulated_tokens.append(token)

                # Extract model from modelResponse (final chunk)
                model_response = response.get("modelResponse", {})
                if model_response:
                    final_message = model_response.get("message")
                    result["model"] = model_response.get("model")
                    result["response_id"] = model_response.get("responseId")
                    # Get request metadata for model info
                    request_meta = model_response.get("requestMetadata", {})
                    if request_meta.get("model"):
                        result["model"] = request_meta.get("model")

                # Get conversation ID from conversation object
                conversation = data.get("result", {}).get("conversation", {})
                if conversation.get("conversationId"):
                    result["conversation_id"] = conversation.get("conversationId")

            except json.JSONDecodeError:
                continue

        # Prefer final message over accumulated tokens
        if final_message:
            result["content"] = final_message
        elif accumulated_tokens:
            result["content"] = "".join(accumulated_tokens)

    except (UnicodeDecodeError, IndexError, TypeError) as e:
        logger.debug(f"Failed to parse Grok response: {e}")

    return result


# ==============================================================================
# JSONata-based Configurable Parsing
# ==============================================================================


class JSONataEvaluator:
    """Wrapper around jsonata-python for expression evaluation."""

    def __init__(self):
        if not JSONATA_AVAILABLE:
            raise RuntimeError("jsonata-python is not installed. Run: pip install jsonata-python")

    def evaluate(self, expression: str, data: Any) -> Any:
        """
        Evaluate a JSONata expression against data.

        Args:
            expression: JSONata expression string
            data: Data to evaluate against

        Returns:
            Result of evaluation, or None on error
        """
        if not expression:
            return None
        try:
            expr = jsonata.Jsonata(expression)
            return expr.evaluate(data)
        except Exception as e:
            logger.debug(f"JSONata evaluation failed for '{expression[:50]}...': {e}")
            return None

    def evaluate_bool(self, expression: str, data: Any) -> bool:
        """Evaluate expression and return as boolean."""
        result = self.evaluate(expression, data)
        return bool(result)


class FormatHandler(ABC):
    """Abstract base for stream format handlers."""

    @abstractmethod
    def process(self, data: bytes) -> list[dict]:
        """
        Process raw bytes and return list of parsed JSON objects.

        Args:
            data: Raw bytes from stream

        Returns:
            List of parsed JSON objects (may be empty)
        """
        pass

    @abstractmethod
    def finalize(self) -> list[dict]:
        """
        Return any remaining buffered data as JSON objects.

        Returns:
            List of remaining JSON objects
        """
        pass


class SSEFormatHandler(FormatHandler):
    """Handler for Server-Sent Events (SSE) format."""

    def __init__(self, options: dict):
        self.prefixes = options.get("prefixes", ["data: "])
        self.skip_values = set(options.get("skip_values", ["[DONE]"]))
        self._buffer = ""

    def process(self, data: bytes) -> list[dict]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return []

        self._buffer += text
        return self._extract_events()

    def _extract_events(self) -> list[dict]:
        objects = []

        # Process double newlines (standard SSE)
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            obj = self._parse_event(event)
            if obj is not None:
                objects.append(obj)

        # Process single newlines for ChatGPT-style events
        lines = self._buffer.split("\n")
        self._buffer = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if this looks like a complete event
            if any(line.startswith(p) for p in self.prefixes):
                obj = self._parse_event(line)
                if obj is not None:
                    objects.append(obj)
            else:
                # Keep incomplete lines in buffer
                self._buffer += line + "\n"

        return objects

    def _parse_event(self, event: str) -> dict | None:
        """Parse a single SSE event."""
        for line in event.strip().split("\n"):
            line = line.strip()
            for prefix in self.prefixes:
                if line.startswith(prefix):
                    data_str = line[len(prefix):]
                    if data_str.strip() in self.skip_values:
                        return None
                    try:
                        return json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
        return None

    def finalize(self) -> list[dict]:
        if not self._buffer.strip():
            return []
        obj = self._parse_event(self._buffer)
        self._buffer = ""
        return [obj] if obj else []


class NDJSONFormatHandler(FormatHandler):
    """Handler for newline-delimited JSON (NDJSON) format."""

    def __init__(self, options: dict):
        self.delimiter = options.get("delimiter", "}{")
        self._buffer = ""

    def process(self, data: bytes) -> list[dict]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return []

        self._buffer += text
        return self._extract_objects()

    def _extract_objects(self) -> list[dict]:
        objects = []

        # Split by delimiter (e.g., "}{")
        parts = self._buffer.split(self.delimiter)
        if len(parts) == 1:
            # No delimiter found, keep in buffer
            return []

        # Process all complete parts
        for i, part in enumerate(parts[:-1]):
            # Reconstruct JSON object boundaries
            json_str = part
            if i > 0 and not json_str.startswith("{"):
                json_str = "{" + json_str
            if not json_str.endswith("}"):
                json_str = json_str + "}"

            try:
                obj = json.loads(json_str)
                objects.append(obj)
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse NDJSON part: {json_str[:100]}")

        # Keep last part in buffer (may be incomplete)
        last = parts[-1]
        if not last.startswith("{"):
            last = "{" + last
        self._buffer = last

        return objects

    def finalize(self) -> list[dict]:
        if not self._buffer.strip():
            return []
        json_str = self._buffer
        if not json_str.endswith("}"):
            json_str = json_str + "}"
        self._buffer = ""
        try:
            return [json.loads(json_str)]
        except json.JSONDecodeError:
            return []


class LengthPrefixedFormatHandler(FormatHandler):
    """Handler for length-prefixed format (Gemini style)."""

    def __init__(self, options: dict):
        self.header_strip = options.get("header_strip", ")]}'")
        self._buffer = b""
        self._header_stripped = False

    def process(self, data: bytes) -> list[dict]:
        self._buffer += data
        return self._extract_chunks()

    def _extract_chunks(self) -> list[dict]:
        objects = []

        # Strip header if not done yet
        if not self._header_stripped:
            try:
                text = self._buffer.decode("utf-8")
                if text.startswith(self.header_strip):
                    text = text[len(self.header_strip):]
                    self._buffer = text.encode("utf-8")
                self._header_stripped = True
            except UnicodeDecodeError:
                pass

        try:
            text = self._buffer.decode("utf-8")
        except UnicodeDecodeError:
            return []

        # Parse length-prefixed chunks
        pos = 0
        while pos < len(text):
            # Skip whitespace
            while pos < len(text) and text[pos] in " \n\r\t":
                pos += 1
            if pos >= len(text):
                break

            # Read length
            length_start = pos
            while pos < len(text) and text[pos].isdigit():
                pos += 1
            if pos == length_start:
                pos += 1
                continue

            try:
                chunk_length = int(text[length_start:pos])
            except ValueError:
                pos += 1
                continue

            # Skip newline
            if pos < len(text) and text[pos] == "\n":
                pos += 1

            # Check if we have the full chunk
            if pos + chunk_length > len(text):
                # Incomplete chunk, put back in buffer
                self._buffer = text[length_start:].encode("utf-8")
                return objects

            # Extract chunk
            chunk = text[pos:pos + chunk_length]
            pos += chunk_length

            try:
                obj = json.loads(chunk)
                objects.append(obj)
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse length-prefixed chunk: {chunk[:100]}")

        self._buffer = text[pos:].encode("utf-8") if pos < len(text) else b""
        return objects

    def finalize(self) -> list[dict]:
        # Try to parse any remaining buffer
        return self._extract_chunks()


class Preprocessor:
    """Handles preprocessing steps for complex data formats."""

    def __init__(self, evaluator: JSONataEvaluator | None = None):
        self.evaluator = evaluator

    def process(self, data: Any, steps: list[dict]) -> Any:
        """
        Apply preprocessing steps to data.

        Args:
            data: Input data
            steps: List of preprocessing operations

        Returns:
            Processed data
        """
        result = data
        for step in steps:
            op = step.get("op")
            if op == "json_parse":
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        logger.debug(f"json_parse failed: {str(result)[:50]}")
                        return None
            elif op == "index":
                value = step.get("value", 0)
                if isinstance(result, (list, tuple)) and value < len(result):
                    result = result[value]
                else:
                    return None
            elif op == "form_decode":
                field = step.get("field")
                if isinstance(result, bytes):
                    try:
                        params = parse_qs(result.decode("utf-8"))
                        result = params.get(field, [None])[0]
                    except (UnicodeDecodeError, IndexError):
                        return None
                elif isinstance(result, dict):
                    result = result.get(field)
            elif op == "strip_prefix":
                prefix = step.get("prefix", "")
                if isinstance(result, str) and result.startswith(prefix):
                    result = result[len(prefix):]

        return result


class ContentAnalyzer:
    """
    Analyzes extracted content for rich elements.

    Uses regex patterns to identify code blocks, links, tables,
    lists, markdown, and other content features.
    """

    # Regex patterns for content analysis
    CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)
    MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    URL_PATTERN = re.compile(r'https?://[^\s<>\[\]()"\',]+[^\s<>\[\]()"\',.]')
    TABLE_PATTERN = re.compile(
        r'^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)+)',
        re.MULTILINE
    )
    HEADER_PATTERN = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
    BOLD_PATTERN = re.compile(r'\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_')
    ORDERED_LIST_PATTERN = re.compile(r'(?:^|\n)(\d+\.\s+.+)', re.MULTILINE)
    UNORDERED_LIST_PATTERN = re.compile(r'(?:^|\n)([-*•]\s+.+)', re.MULTILINE)
    CHECKLIST_PATTERN = re.compile(r'(?:^|\n)(-\s+\[[ xX]\]\s+.+)', re.MULTILINE)
    EMOJI_PATTERN = re.compile(
        r'[\U0001F300-\U0001F9FF]|[\U00002600-\U000027BF]|[\U0001F600-\U0001F64F]'
    )
    MATH_PATTERN = re.compile(r'\$\$?.+?\$\$?', re.DOTALL)

    # ChatGPT entity markers
    CHATGPT_ENTITY_PATTERN = re.compile(r'\ue200entity\ue202\[([^\]]+)\]\ue201')
    CHATGPT_CITE_PATTERN = re.compile(r'\ue200cite\ue202([^\ue201]+)\ue201')

    def analyze(self, content: str) -> dict:
        """
        Analyze content and return analysis dict.

        Args:
            content: The response content text

        Returns:
            Dict with stats, code_blocks, hyperlinks, tables, etc.
        """
        if not content:
            return {}

        result: dict[str, Any] = {
            "stats": {
                "chars": len(content),
                "words": len(content.split()),
                "lines": content.count('\n') + 1,
            },
            "flags": {
                "has_markdown": self._has_markdown(content),
                "has_emoji": bool(self.EMOJI_PATTERN.search(content)),
                "has_math": bool(self.MATH_PATTERN.search(content)),
            },
        }

        # Extract code blocks
        code_blocks = self._extract_code_blocks(content)
        if code_blocks:
            result["code_blocks"] = code_blocks

        # Extract hyperlinks
        hyperlinks = self._extract_hyperlinks(content)
        if hyperlinks:
            result["hyperlinks"] = hyperlinks

        # Extract tables
        tables = self._extract_tables(content)
        if tables:
            result["tables"] = tables

        # Extract lists
        lists = self._extract_lists(content)
        if lists:
            result["lists"] = lists

        # Extract ChatGPT-specific elements
        entities = self._extract_chatgpt_entities(content)
        if entities:
            result["entities"] = entities

        citations = self._extract_chatgpt_citations(content)
        if citations:
            result["citations"] = citations

        return result

    def _extract_code_blocks(self, content: str) -> list[dict]:
        """Extract fenced code blocks."""
        blocks = []
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or None
            code = match.group(2).strip()
            blocks.append({
                "type": "code",
                "language": language,
                "code": code,
                "line_count": code.count('\n') + 1,
            })
        return blocks

    def _extract_hyperlinks(self, content: str) -> list[dict]:
        """Extract markdown links and raw URLs."""
        links = []
        seen_urls: set[str] = set()

        # Markdown links [text](url)
        for match in self.MARKDOWN_LINK_PATTERN.finditer(content):
            text = match.group(1)
            url = match.group(2)
            if url not in seen_urls:
                seen_urls.add(url)
                links.append({"type": "link", "url": url, "text": text})

        # Raw URLs
        for match in self.URL_PATTERN.finditer(content):
            url = match.group(0)
            if url not in seen_urls:
                seen_urls.add(url)
                links.append({"type": "link", "url": url})

        return links

    def _extract_tables(self, content: str) -> list[dict]:
        """Extract markdown tables."""
        tables = []
        for match in self.TABLE_PATTERN.finditer(content):
            header_row = match.group(1)
            body_rows = match.group(2)

            headers = [h.strip() for h in header_row.split('|') if h.strip()]
            rows = []
            for row_line in body_rows.strip().split('\n'):
                cells = [c.strip() for c in row_line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)

            if headers and rows:
                tables.append({
                    "type": "table",
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                })
        return tables

    def _extract_lists(self, content: str) -> list[dict]:
        """Extract ordered, unordered, and checklists."""
        lists = []

        # Checklist
        checklist_matches = self.CHECKLIST_PATTERN.findall(content)
        if checklist_matches:
            items = [m.strip() for m in checklist_matches]
            if items:
                lists.append({
                    "type": "list",
                    "list_type": "checklist",
                    "items": items,
                    "item_count": len(items),
                })

        # Ordered
        ordered_matches = self.ORDERED_LIST_PATTERN.findall(content)
        if ordered_matches:
            items = [re.sub(r'^\d+\.\s+', '', m.strip()) for m in ordered_matches]
            if items:
                lists.append({
                    "type": "list",
                    "list_type": "ordered",
                    "items": items,
                    "item_count": len(items),
                })

        # Unordered
        unordered_matches = self.UNORDERED_LIST_PATTERN.findall(content)
        if unordered_matches:
            items = [re.sub(r'^[-*•]\s+', '', m.strip()) for m in unordered_matches]
            if items:
                lists.append({
                    "type": "list",
                    "list_type": "unordered",
                    "items": items,
                    "item_count": len(items),
                })

        return lists

    def _extract_chatgpt_entities(self, content: str) -> list[dict]:
        """Extract ChatGPT entity markers."""
        entities = []
        for match in self.CHATGPT_ENTITY_PATTERN.finditer(content):
            entity_data = match.group(1)
            try:
                parts = json.loads(f'[{entity_data}]')
                if len(parts) >= 2:
                    entity_id = parts[0] if isinstance(parts[0], str) else None
                    name = parts[1] if isinstance(parts[1], str) else str(parts[1])

                    entity_type = "other"
                    if entity_id:
                        if "business" in entity_id:
                            entity_type = "business"
                        elif "location" in entity_id or "place" in entity_id:
                            entity_type = "location"
                        elif "person" in entity_id:
                            entity_type = "person"
                        elif "org" in entity_id:
                            entity_type = "organization"

                    entities.append({
                        "type": "entity",
                        "entity_type": entity_type,
                        "name": name,
                        "id": entity_id,
                    })
            except (json.JSONDecodeError, IndexError, TypeError):
                entities.append({
                    "type": "entity",
                    "entity_type": "other",
                    "name": entity_data,
                })
        return entities

    def _extract_chatgpt_citations(self, content: str) -> list[dict]:
        """Extract ChatGPT citation markers."""
        citations = []
        seen_ids: set[str] = set()
        for match in self.CHATGPT_CITE_PATTERN.finditer(content):
            cite_data = match.group(1)
            for cite_id in cite_data.split('\ue202'):
                cite_id = cite_id.strip()
                if cite_id and cite_id not in seen_ids:
                    seen_ids.add(cite_id)
                    citations.append({
                        "type": "citation",
                        "id": cite_id,
                        "source": "chatgpt_search" if "search" in cite_id else None,
                    })
        return citations

    def _has_markdown(self, content: str) -> bool:
        """Check if content contains markdown formatting."""
        return bool(
            self.HEADER_PATTERN.search(content) or
            self.BOLD_PATTERN.search(content) or
            self.CODE_BLOCK_PATTERN.search(content) or
            self.TABLE_PATTERN.search(content) or
            self.MARKDOWN_LINK_PATTERN.search(content)
        )


# Module-level content analyzer instance
_content_analyzer = ContentAnalyzer()


def analyze_content(content: str) -> dict:
    """
    Analyze content for rich elements (code blocks, links, tables, etc.).

    Args:
        content: The response content text

    Returns:
        Dict with analysis results
    """
    return _content_analyzer.analyze(content)


class ConfigurableStreamBuffer:
    """
    Data-driven stream processor.

    Uses configuration from websites.json to extract and accumulate
    values from streaming responses.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Stream configuration from websites.json
        """
        self.config = config
        self.evaluator = JSONataEvaluator() if JSONATA_AVAILABLE else None
        self.preprocessor = Preprocessor(self.evaluator)
        self.accumulated: dict[str, Any] = {}
        self.format_handler = self._create_format_handler()

    def _create_format_handler(self) -> FormatHandler:
        """Create appropriate format handler based on config."""
        format_type = self.config.get("format", "sse")
        options = self.config.get("format_options", {})

        if format_type == "sse":
            return SSEFormatHandler(options)
        elif format_type == "ndjson":
            return NDJSONFormatHandler(options)
        elif format_type == "length_prefixed":
            return LengthPrefixedFormatHandler(options)
        else:
            logger.warning(f"Unknown stream format: {format_type}, defaulting to SSE")
            return SSEFormatHandler(options)

    def process_chunk(self, chunk: bytes) -> bytes:
        """
        Process a chunk from the stream.

        Args:
            chunk: Raw bytes from stream

        Returns:
            Original chunk (pass-through)
        """
        if not chunk:
            return chunk

        # Parse into JSON objects
        json_objects = self.format_handler.process(chunk)

        # Apply rules to each object
        for obj in json_objects:
            self._apply_rules(obj)

        return chunk

    def _apply_rules(self, obj: dict) -> None:
        """Apply extraction rules to a JSON object."""
        if not self.evaluator:
            return

        # Debug: log the object being processed
        obj_preview = str(obj)[:200] if obj else "None"
        logger.debug(f"Processing SSE object: {obj_preview}")

        for rule in self.config.get("rules", []):
            # Check condition
            when = rule.get("when", "true")
            try:
                matched = self.evaluator.evaluate_bool(when, obj)
                if not matched:
                    continue
                logger.debug(f"Rule matched: when='{when}'")
            except Exception as e:
                logger.debug(f"Rule condition failed: when='{when}', error={e}")
                continue

            # Apply preprocessing if any
            preprocess_steps = rule.get("preprocess", [])
            processed = self.preprocessor.process(obj, preprocess_steps) if preprocess_steps else obj

            if processed is None:
                continue

            # Extract values
            for field, expr in rule.get("extract", {}).items():
                value = self.evaluator.evaluate(expr, processed)
                if value is not None:
                    logger.debug(f"Extracted {field}={repr(value)[:100]}")
                    self._accumulate(field, value)

    def _accumulate(self, field: str, value: Any) -> None:
        """Accumulate a value based on configuration."""
        acc_config = self.config.get("accumulate", {}).get(field, {})
        op = acc_config.get("op", "last")

        if op == "concat":
            current = self.accumulated.get(field, "")
            self.accumulated[field] = str(current) + str(value)
        elif op == "first":
            if field not in self.accumulated:
                self.accumulated[field] = value
        elif op == "last":
            self.accumulated[field] = value
        elif op == "sum":
            current = self.accumulated.get(field, 0)
            try:
                self.accumulated[field] = current + float(value)
            except (ValueError, TypeError):
                pass

    def finalize(self) -> dict:
        """
        Finalize the buffer and return accumulated data.

        Returns:
            Dict with content, model, etc.
        """
        # Process any remaining buffered data
        remaining = self.format_handler.finalize()
        for obj in remaining:
            self._apply_rules(obj)

        # Apply finalize expressions
        result = {}
        finalize_config = self.config.get("finalize", {})

        if self.evaluator and finalize_config:
            context = {"accumulated": self.accumulated}
            for field, expr in finalize_config.items():
                value = self.evaluator.evaluate(expr, context)
                result[field] = value
        else:
            # Default: just return accumulated values
            result = dict(self.accumulated)

        # Ensure we have standard fields
        if "content" not in result:
            result["content"] = self.accumulated.get("content")
        if "model" not in result:
            result["model"] = self.accumulated.get("model")

        logger.info(f"ConfigurableStreamBuffer finalized: content_len={len(result.get('content') or '')} model={result.get('model')}")

        return result


class ConfigurableRequestParser:
    """
    Data-driven request parser using JSONata.

    Uses configuration from websites.json to extract request fields.
    """

    def __init__(self):
        self.evaluator = JSONataEvaluator() if JSONATA_AVAILABLE else None
        self.preprocessor = Preprocessor(self.evaluator)

    def parse(
        self,
        body: bytes,
        config: dict,
        include_raw: bool = True,
    ) -> InteractionRequest:
        """
        Parse request body using config.

        Args:
            body: Raw request body bytes
            config: Parser configuration dict
            include_raw: Whether to include raw body

        Returns:
            Parsed InteractionRequest
        """
        # Decode body based on encoding
        encoding = config.get("encoding", "json")
        preprocess_steps = config.get("preprocess", [])

        if encoding == "form":
            form_field = config.get("form_field")
            preprocess_steps = [{"op": "form_decode", "field": form_field}] + preprocess_steps
            data = self.preprocessor.process(body, preprocess_steps)
        elif encoding == "json":
            try:
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return InteractionRequest(raw=None)
            if preprocess_steps:
                data = self.preprocessor.process(data, preprocess_steps)
        else:
            try:
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return InteractionRequest(raw=None)

        if data is None:
            return InteractionRequest(raw=None)

        # Extract fields using JSONata
        if not self.evaluator:
            return InteractionRequest(raw=data if include_raw else None)

        # Extract prompt/messages
        prompt = self._extract(config.get("prompt"), data)
        messages_expr = config.get("messages")
        if messages_expr:
            messages = self._extract(messages_expr, data)
        elif prompt:
            messages = [{"role": "user", "content": str(prompt)}]
        else:
            messages = None

        return InteractionRequest(
            messages=messages,
            model=self._extract(config.get("model"), data),
            temperature=self._extract(config.get("temperature"), data),
            max_tokens=self._extract(config.get("max_tokens"), data),
            tools=self._extract(config.get("tools"), data),
            raw=data if include_raw else None,
        )

    def _extract(self, expr: str | None, data: Any) -> Any:
        """Extract value using JSONata."""
        if not expr or not self.evaluator:
            return None
        return self.evaluator.evaluate(expr, data)
