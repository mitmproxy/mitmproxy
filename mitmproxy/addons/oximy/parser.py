"""
Request/Response parsing using JSONPath extraction.

Extracts structured data (messages, model, usage, etc.) from
AI API requests and responses based on OISP parser configurations.

Supports:
- Standard JSON APIs (OpenAI, Anthropic, etc.)
- Form-encoded requests (Gemini)
- Custom JSON structures (DeepSeek)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import parse_qs

from mitmproxy.addons.oximy.models import InteractionRequest, InteractionResponse

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
