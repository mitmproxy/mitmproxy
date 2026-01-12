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
from abc import ABC
from abc import abstractmethod
from typing import Any

try:
    import jsonata

    JSONATA_AVAILABLE = True
except ImportError:
    JSONATA_AVAILABLE = False
    jsonata = None

from models import InteractionRequest
from models import InteractionResponse

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
            content=content
            if isinstance(content, str)
            else str(content)
            if content
            else None,
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
                already_mapped = any(
                    key in pk for _, pk in key_mappings if key in normalized
                )
                if not already_mapped:
                    normalized[key] = value

        return normalized


# ==============================================================================
# JSONata-based Configurable Parsing
# ==============================================================================


class JSONataEvaluator:
    """Wrapper around jsonata-python for expression evaluation."""

    def __init__(self):
        if not JSONATA_AVAILABLE:
            raise RuntimeError(
                "jsonata-python is not installed. Run: pip install jsonata-python"
            )

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
            logger.info(
                f"JSONata.evaluate: expr='{expression}', data_type={type(data).__name__}"
            )
            expr = jsonata.Jsonata(expression)
            result = expr.evaluate(data)
            logger.info(
                f"JSONata.evaluate: result_type={type(result).__name__}, result={str(result)[:200] if result else None}"
            )
            return result
        except Exception as e:
            logger.info(f"JSONata evaluation EXCEPTION for '{expression}': {e}")
            return None

    def evaluate_bool(self, expression: str, data: Any) -> bool:
        """Evaluate expression and return as boolean."""
        result = self.evaluate(expression, data)
        logger.info(
            f"JSONata.evaluate_bool: expr='{expression}', result={result}, bool={bool(result)}"
        )
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
        """
        Extract complete SSE events from buffer.

        SSE events are separated by double newlines.
        Handles both \n\n and \r\n\r\n delimiters.
        """
        objects = []

        # Normalize line endings - some servers use \r\n
        self._buffer = self._buffer.replace("\r\n", "\n")

        # Standard SSE: events are separated by double newlines
        # Process all complete events (ending with \n\n)
        while "\n\n" in self._buffer:
            event, self._buffer = self._buffer.split("\n\n", 1)
            obj = self._parse_event(event)
            if obj is not None:
                objects.append(obj)

        return objects

    def _parse_event(self, event: str) -> dict | None:
        """Parse a single SSE event, extracting JSON from data: lines."""
        for line in event.strip().split("\n"):
            line = line.strip()
            for prefix in self.prefixes:
                if line.startswith(prefix):
                    data_str = line[len(prefix) :]
                    if data_str.strip() in self.skip_values:
                        return None
                    try:
                        return json.loads(data_str)
                    except json.JSONDecodeError:
                        # JSON incomplete or invalid, skip this line
                        continue
        return None

    def finalize(self) -> list[dict]:
        """Process any remaining buffer content."""
        # Normalize line endings
        self._buffer = self._buffer.replace("\r\n", "\n")

        if not self._buffer.strip():
            return []

        # Try to parse remaining buffer as events
        results = []
        parts = self._buffer.split("\n\n")
        for part in parts:
            if part.strip():
                obj = self._parse_event(part)
                if obj is not None:
                    results.append(obj)
        self._buffer = ""
        return results


class NDJSONFormatHandler(FormatHandler):
    """Handler for newline-delimited JSON (NDJSON) format.

    Supports multiple delimiter types:
    - Standard NDJSON: newline-separated complete JSON objects
    - Concatenated JSON: }{ delimiter between objects (Grok style)
    - Custom delimiters: any string separator between objects (Granola style)
    """

    def __init__(self, options: dict):
        self.delimiter = options.get("delimiter", "}{")
        # Check if this is a custom string delimiter (not }{)
        self._is_custom_delimiter = self.delimiter != "}{"
        self._buffer = ""
        logger.debug(
            f"NDJSONFormatHandler initialized with delimiter='{self.delimiter}', custom={self._is_custom_delimiter}"
        )

    def process(self, data: bytes) -> list[dict]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return []

        self._buffer += text
        logger.info(
            f"NDJSON process: received {len(text)} chars, buffer now {len(self._buffer)} chars"
        )
        objects = self._extract_objects()
        if objects:
            logger.info(f"NDJSON extracted {len(objects)} objects")
        return objects

    def _extract_objects(self) -> list[dict]:
        objects = []

        # Handle custom string delimiters (e.g., "-----CHUNK_BOUNDARY-----" for Granola)
        # These delimiters separate complete JSON objects, no reconstruction needed
        if self._is_custom_delimiter and self.delimiter in self._buffer:
            parts = self._buffer.split(self.delimiter)
            logger.info(
                f"NDJSON split by custom delimiter '{self.delimiter[:20]}...' into {len(parts)} parts"
            )

            # Process all complete parts (all but last which may be incomplete)
            for i, part in enumerate(parts[:-1]):
                json_str = part.strip()
                if not json_str:
                    continue
                try:
                    obj = json.loads(json_str)
                    objects.append(obj)
                    logger.debug(f"NDJSON parsed part {i}: keys={list(obj.keys())[:5]}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse NDJSON part {i}: {e}, json_str={json_str[:100]}"
                    )

            # Keep last part in buffer (may be incomplete)
            self._buffer = parts[-1]

            if objects:
                logger.info(
                    f"NDJSON extracted {len(objects)} objects from custom delimiter split"
                )
                return objects

        # Handle }{ delimiter - concatenated JSON objects like Grok
        # {"result":{...}}{"result":{...}}
        if not self._is_custom_delimiter and self.delimiter in self._buffer:
            parts = self._buffer.split(self.delimiter)
            logger.info(f"NDJSON split by '{self.delimiter}' into {len(parts)} parts")

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
                    logger.debug(f"NDJSON parsed part {i}: keys={list(obj.keys())[:5]}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse NDJSON part {i}: {e}, json_str={json_str[:100]}"
                    )

            # Keep last part in buffer (may be incomplete)
            last = parts[-1]
            if not last.startswith("{"):
                last = "{" + last
            self._buffer = last

            if objects:
                logger.info(
                    f"NDJSON extracted {len(objects)} objects from delimiter split"
                )
                return objects

        # Fallback: Try newline-delimited (standard NDJSON with one object per line)
        # Only if buffer contains newlines AND starts with a complete JSON object on first line
        if "\n" in self._buffer and self._buffer.strip().startswith("{"):
            lines = self._buffer.split("\n")
            complete_lines = lines[:-1]  # All but last (may be incomplete)

            for line in complete_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    objects.append(obj)
                    logger.debug(f"NDJSON parsed line: keys={list(obj.keys())[:5]}")
                except json.JSONDecodeError:
                    # Not valid JSON line, skip
                    pass

            if objects:
                self._buffer = lines[-1]  # Keep last line in buffer
                logger.info(
                    f"NDJSON extracted {len(objects)} objects from newline split"
                )
                return objects

        logger.debug(
            f"NDJSON buffer now {len(self._buffer)} chars, no complete objects yet"
        )
        return objects

    def finalize(self) -> list[dict]:
        logger.info(
            f"NDJSON finalize: buffer={len(self._buffer)} chars, first 200={self._buffer[:200]}"
        )
        if not self._buffer.strip():
            return []

        results = []

        # For custom delimiters, just try to parse the remaining buffer as-is
        if self._is_custom_delimiter:
            json_str = self._buffer.strip()
            if json_str:
                try:
                    obj = json.loads(json_str)
                    results.append(obj)
                    logger.debug(f"NDJSON finalize parsed: keys={list(obj.keys())[:5]}")
                except json.JSONDecodeError as e:
                    logger.debug(
                        f"NDJSON finalize failed: {e}, json_str={json_str[:100]}"
                    )
            self._buffer = ""
            return results

        # For }{ delimiter, try to parse remaining buffer with reconstruction
        for line in self._buffer.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Add closing brace if needed
            json_str = line
            if not json_str.endswith("}"):
                json_str = json_str + "}"
            try:
                obj = json.loads(json_str)
                results.append(obj)
                logger.debug(f"NDJSON finalize parsed: keys={list(obj.keys())[:5]}")
            except json.JSONDecodeError as e:
                logger.debug(
                    f"NDJSON finalize line failed: {e}, json_str={json_str[:100]}"
                )

        self._buffer = ""
        return results


class LengthPrefixedFormatHandler(FormatHandler):
    """Handler for length-prefixed format (Gemini style)."""

    def __init__(self, options: dict):
        header_strip = options.get("header_strip", ")]}'")
        # Handle escape sequences from JSON config (\\n -> \n)
        self.header_strip = header_strip.encode().decode("unicode_escape")
        self._buffer = b""
        self._header_stripped = False
        logger.info(
            f"LengthPrefixedFormatHandler init: header_strip={repr(self.header_strip)}"
        )

    def process(self, data: bytes) -> list[dict]:
        self._buffer += data
        logger.info(
            f"LengthPrefixed process: received {len(data)} bytes, buffer now {len(self._buffer)} bytes"
        )
        chunks = self._extract_chunks()
        logger.info(f"LengthPrefixed extracted {len(chunks)} chunks")
        return chunks

    def _extract_chunks(self) -> list[dict]:
        objects = []

        # Strip header if not done yet
        if not self._header_stripped:
            try:
                text = self._buffer.decode("utf-8")
                logger.info(
                    f"LengthPrefixed checking header: starts_with={repr(text[:20])}, header_strip={repr(self.header_strip)}"
                )
                if text.startswith(self.header_strip):
                    text = text[len(self.header_strip) :]
                    self._buffer = text.encode("utf-8")
                    logger.info(
                        f"LengthPrefixed header stripped, buffer now starts with: {repr(text[:50])}"
                    )
                else:
                    logger.info(f"LengthPrefixed header NOT found at start")
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
            chunk = text[pos : pos + chunk_length]
            logger.info(
                f"LengthPrefixed: length={chunk_length}, chunk_start={repr(chunk[:50])}, chunk_end={repr(chunk[-50:])}"
            )
            pos += chunk_length

            try:
                # Strip trailing whitespace - length sometimes includes newline
                chunk_stripped = chunk.rstrip()
                obj = json.loads(chunk_stripped)
                objects.append(obj)
                logger.info(
                    f"LengthPrefixed parsed chunk: type={type(obj).__name__}, preview={str(obj)[:200]}"
                )
            except json.JSONDecodeError as e:
                logger.info(
                    f"Failed to parse length-prefixed chunk: {e}, len={len(chunk)}, stripped_len={len(chunk_stripped)}"
                )

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
            logger.info(
                f"Preprocess op={op}, input type={type(result).__name__}, preview={str(result)[:200]}"
            )
            if op == "json_parse":
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                        logger.info(
                            f"json_parse success: type={type(result).__name__}, preview={str(result)[:200]}"
                        )
                    except json.JSONDecodeError as e:
                        logger.info(
                            f"json_parse failed: {e}, input={str(result)[:100]}"
                        )
                        return None
                else:
                    logger.info(
                        f"json_parse skipped: input is not string, is {type(result).__name__}"
                    )
            elif op == "index":
                value = step.get("value", 0)
                if isinstance(result, (list, tuple)) and value < len(result):
                    result = result[value]
                    logger.info(
                        f"index {value} success: type={type(result).__name__}, preview={str(result)[:200]}"
                    )
                else:
                    logger.info(
                        f"index {value} failed: result is {type(result).__name__}, len={len(result) if hasattr(result, '__len__') else 'N/A'}"
                    )
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
                    result = result[len(prefix) :]

        return result


class ContentAnalyzer:
    """
    Analyzes extracted content for rich elements.

    Uses regex patterns to identify code blocks, links, tables,
    lists, markdown, and other content features.
    """

    # Regex patterns for content analysis
    CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    URL_PATTERN = re.compile(r'https?://[^\s<>\[\]()"\',]+[^\s<>\[\]()"\',.]')
    TABLE_PATTERN = re.compile(
        r"^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)+)", re.MULTILINE
    )
    HEADER_PATTERN = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
    BOLD_PATTERN = re.compile(r"\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_")
    ORDERED_LIST_PATTERN = re.compile(r"(?:^|\n)(\d+\.\s+.+)", re.MULTILINE)
    UNORDERED_LIST_PATTERN = re.compile(r"(?:^|\n)([-*•]\s+.+)", re.MULTILINE)
    CHECKLIST_PATTERN = re.compile(r"(?:^|\n)(-\s+\[[ xX]\]\s+.+)", re.MULTILINE)
    EMOJI_PATTERN = re.compile(
        r"[\U0001F300-\U0001F9FF]|[\U00002600-\U000027BF]|[\U0001F600-\U0001F64F]"
    )
    MATH_PATTERN = re.compile(r"\$\$?.+?\$\$?", re.DOTALL)

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
                "lines": content.count("\n") + 1,
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

        return result

    def _extract_code_blocks(self, content: str) -> list[dict]:
        """Extract fenced code blocks."""
        blocks = []
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or None
            code = match.group(2).strip()
            blocks.append(
                {
                    "type": "code",
                    "language": language,
                    "code": code,
                    "line_count": code.count("\n") + 1,
                }
            )
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

            headers = [h.strip() for h in header_row.split("|") if h.strip()]
            rows = []
            for row_line in body_rows.strip().split("\n"):
                cells = [c.strip() for c in row_line.split("|") if c.strip()]
                if cells:
                    rows.append(cells)

            if headers and rows:
                tables.append(
                    {
                        "type": "table",
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows),
                    }
                )
        return tables

    def _extract_lists(self, content: str) -> list[dict]:
        """Extract ordered, unordered, and checklists."""
        lists = []

        # Checklist
        checklist_matches = self.CHECKLIST_PATTERN.findall(content)
        if checklist_matches:
            items = [m.strip() for m in checklist_matches]
            if items:
                lists.append(
                    {
                        "type": "list",
                        "list_type": "checklist",
                        "items": items,
                        "item_count": len(items),
                    }
                )

        # Ordered
        ordered_matches = self.ORDERED_LIST_PATTERN.findall(content)
        if ordered_matches:
            items = [re.sub(r"^\d+\.\s+", "", m.strip()) for m in ordered_matches]
            if items:
                lists.append(
                    {
                        "type": "list",
                        "list_type": "ordered",
                        "items": items,
                        "item_count": len(items),
                    }
                )

        # Unordered
        unordered_matches = self.UNORDERED_LIST_PATTERN.findall(content)
        if unordered_matches:
            items = [re.sub(r"^[-*•]\s+", "", m.strip()) for m in unordered_matches]
            if items:
                lists.append(
                    {
                        "type": "list",
                        "list_type": "unordered",
                        "items": items,
                        "item_count": len(items),
                    }
                )

        return lists

    def _has_markdown(self, content: str) -> bool:
        """Check if content contains markdown formatting."""
        return bool(
            self.HEADER_PATTERN.search(content)
            or self.BOLD_PATTERN.search(content)
            or self.CODE_BLOCK_PATTERN.search(content)
            or self.TABLE_PATTERN.search(content)
            or self.MARKDOWN_LINK_PATTERN.search(content)
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
        logger.info(f"process_chunk called with {len(chunk)} bytes")

        if not chunk:
            logger.info("process_chunk: empty chunk, returning")
            return chunk

        # Parse into JSON objects
        logger.info(
            f"process_chunk: calling format_handler.process (handler type={type(self.format_handler).__name__})"
        )
        json_objects = self.format_handler.process(chunk)
        logger.info(
            f"process_chunk: format_handler returned {len(json_objects)} JSON objects"
        )

        # Apply rules to each object
        for i, obj in enumerate(json_objects):
            logger.info(
                f"process_chunk: applying rules to object {i}/{len(json_objects)}"
            )
            self._apply_rules(obj)

        logger.info(
            f"process_chunk: done, accumulated so far: {list(self.accumulated.keys())}"
        )
        return chunk

    def _apply_rules(self, obj: dict) -> None:
        """Apply extraction rules to a JSON object."""
        logger.info(
            f"_apply_rules called with obj type={type(obj).__name__}, preview={str(obj)[:300]}"
        )

        if not self.evaluator:
            logger.info("_apply_rules: No evaluator available, returning")
            return

        rules = self.config.get("rules", [])
        logger.info(f"_apply_rules: Found {len(rules)} rules to check")

        for i, rule in enumerate(rules):
            # Check condition
            when = rule.get("when", "true")
            logger.info(f"_apply_rules: Checking rule {i}, when='{when}'")
            try:
                matched = self.evaluator.evaluate_bool(when, obj)
                logger.info(f"_apply_rules: Rule {i} matched={matched}")
                if not matched:
                    continue
            except Exception as e:
                logger.info(
                    f"_apply_rules: Rule {i} condition exception: when='{when}', error={e}"
                )
                continue

            logger.info(f"Rule matched: when='{when}'")

            # Apply preprocessing if any
            preprocess_steps = rule.get("preprocess", [])
            logger.info(f"_apply_rules: preprocess_steps={preprocess_steps}")
            processed = (
                self.preprocessor.process(obj, preprocess_steps)
                if preprocess_steps
                else obj
            )

            if processed is None:
                logger.info(
                    f"_apply_rules: preprocessing returned None, skipping this rule"
                )
                continue

            logger.info(
                f"_apply_rules: after preprocessing, type={type(processed).__name__}, preview={str(processed)[:300]}"
            )

            # Extract values
            for field, expr in rule.get("extract", {}).items():
                # Check for special extraction markers (Python fallbacks)
                if expr == "$_perplexity_blocks":
                    value = self._extract_perplexity_content(processed)
                else:
                    logger.info(
                        f"Evaluating JSONata expr='{expr}' on data type={type(processed).__name__}, preview={str(processed)[:200]}"
                    )
                    value = self.evaluator.evaluate(expr, processed)

                if value is not None and value != "":
                    logger.info(f"Extracted {field}={str(value)[:100]}...")
                    self._accumulate(field, value)
                else:
                    logger.info(
                        f"Extraction returned None/empty for {field} with expr={expr}"
                    )

    def _extract_perplexity_content(self, obj: dict) -> str | None:
        """
        Extract content from Perplexity's complex nested structure.

        Perplexity sends blocks with intended_usage containing 'markdown'
        containing diff_block.patches[].value which can be:
        - A dict with 'chunks' array
        - A string directly (the content)
        """
        blocks = obj.get("blocks", [])
        if not blocks:
            return None

        all_chunks = []
        for block in blocks:
            intended_usage = block.get("intended_usage", "")
            # Match any markdown block (ask_text_0_markdown, etc.)
            if "markdown" in intended_usage.lower():
                diff_block = block.get("diff_block", {})
                patches = diff_block.get("patches", [])
                for patch in patches:
                    value = patch.get("value")
                    if value is None:
                        continue
                    # value can be a string or a dict with chunks
                    if isinstance(value, str):
                        all_chunks.append(value)
                    elif isinstance(value, dict):
                        chunks = value.get("chunks", [])
                        if chunks:
                            all_chunks.extend(str(c) for c in chunks)

        if all_chunks:
            return "".join(all_chunks)
        return None

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
        logger.info(
            f"finalize called, accumulated so far: {list(self.accumulated.keys())}"
        )
        logger.info(
            f"finalize: accumulated values preview: { {k: str(v)[:100] for k, v in self.accumulated.items()} }"
        )

        # Process any remaining buffered data
        remaining = self.format_handler.finalize()
        logger.info(
            f"finalize: format_handler.finalize() returned {len(remaining)} remaining objects"
        )
        for obj in remaining:
            self._apply_rules(obj)

        logger.info(
            f"finalize: after processing remaining, accumulated: {list(self.accumulated.keys())}"
        )

        # Apply finalize expressions
        result = {}
        finalize_config = self.config.get("finalize", {})
        logger.info(f"finalize: finalize_config={finalize_config}")

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

        logger.info(
            f"ConfigurableStreamBuffer finalized: content_len={len(result.get('content') or '')} model={result.get('model')}"
        )

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
            preprocess_steps = [
                {"op": "form_decode", "field": form_field}
            ] + preprocess_steps
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
        else:
            messages = None

        return InteractionRequest(
            prompt=str(prompt) if prompt else None,
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
