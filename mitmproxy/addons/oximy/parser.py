"""
Request/Response parsing using JSONPath extraction.

Extracts structured data (messages, model, usage, etc.) from
AI API requests and responses based on OISP parser configurations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

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
