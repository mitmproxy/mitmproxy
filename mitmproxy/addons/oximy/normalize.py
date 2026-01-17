"""Body content normalization for trace capture."""

from __future__ import annotations

import base64
import json
import re
import urllib.parse

from mitmproxy.net.encoding import decode_gzip, decode_deflate, decode_zstd

# Magic bytes for format detection
GZIP_MAGIC = b'\x1f\x8b'
ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'
ZLIB_PREFIXES = (b'\x78\x01', b'\x78\x9c', b'\x78\xda')

# MessagePack markers (fixmap 0x80-0x8f, fixarray 0x90-0x9f, map16/32, array16/32)
MSGPACK_MARKERS = frozenset(range(0x80, 0xa0)) | {0xdc, 0xdd, 0xde, 0xdf}

# Patterns
BASE64_PATTERN = re.compile(rb'^[A-Za-z0-9+/]+={0,2}$')
BASE64_URL_PATTERN = re.compile(rb'^[A-Za-z0-9_-]+={0,2}$')
URL_ENCODED_PATTERN = re.compile(rb'%[0-9A-Fa-f]{2}')

# Anti-JSON-hijacking prefixes (used by various APIs to prevent XSSI attacks)
# These prefixes make the response invalid JS, preventing script tag exploitation
ANTI_HIJACK_PREFIXES = (
    b")]}'\n",      # Google, etc.
    b")]}'",        # Variant without newline
    b"for(;;);",    # Facebook style
    b"while(1);",   # Alternative loop prefix
    b"{}&&",        # Empty object prefix
)

MAX_DECODE_LAYERS = 3
# MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
MIN_BASE64_LENGTH = 20  # Reduce false positives


def normalize_body(content: bytes | None, content_type: str | None = None) -> str:
    """
    Normalize body content by decoding various encodings.
    NEVER raises - always returns a string.

    Args:
        content: Raw body bytes
        content_type: Optional Content-Type header for format hints
    """
    if not content:
        return ""

    # Handle anti-JSON-hijacking prefixed responses
    # These start with prefixes like )]}'\n, for(;;);, etc.
    if _has_anti_hijack_prefix(content):
        return _normalize_anti_hijack_stream(content)

    # Handle SSE streams (based on content-type)
    if _is_sse_stream(content_type):
        result, _ = _normalize_sse(content)
        return result

    # Handle MessagePack
    if _is_msgpack(content):
        decoded = _decode_msgpack(content)
        if decoded is not None:
            return decoded

    # Try layered decoding (base64, compression, url encoding)
    decoded = _decode_layers(content)
    return _to_string(decoded)


def _to_string(content: bytes) -> str:
    """Convert bytes to string with fallbacks."""
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        # Check if mostly text (>50% printable ASCII) or mostly binary
        printable = sum(1 for b in content if 32 <= b < 127 or b in (9, 10, 13))
        if len(content) > 0 and printable / len(content) > 0.5:
            return content.decode('utf-8', errors='replace')
        return content.hex()


def _is_sse_stream(content_type: str) -> bool:
    """Detect SSE stream format (data: lines)."""
    if content_type == "text/event-stream; charset=utf-8":
        return True
    else:
        return False


def _has_anti_hijack_prefix(content: bytes) -> bool:
    """Detect anti-JSON-hijacking prefixed responses.

    These prefixes (like )]}', for(;;);, while(1);) are used to prevent
    XSSI attacks by making responses invalid JavaScript.
    """
    return any(content.startswith(prefix) for prefix in ANTI_HIJACK_PREFIXES)


def _get_anti_hijack_prefix(content: bytes) -> bytes | None:
    """Return the matching anti-hijack prefix, or None."""
    for prefix in ANTI_HIJACK_PREFIXES:
        if content.startswith(prefix):
            return prefix
    return None


def _normalize_anti_hijack_stream(content: bytes) -> str:
    """Parse anti-hijack prefixed response and extract JSON content.

    Handles both:
    - Simple JSON after prefix
    - Length-prefixed streaming chunks (number\njson\nnumber\njson...)
    """
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        return _to_string(content)

    # Remove the anti-hijack prefix
    prefix = _get_anti_hijack_prefix(content)
    if prefix:
        text = text[len(prefix):].lstrip('\n')

    chunks = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if it's a length prefix (number)
        if line.isdigit():
            length = int(line)
            i += 1

            # Collect the JSON content (may span multiple lines)
            json_content = []
            collected_length = 0

            while i < len(lines) and collected_length < length:
                json_content.append(lines[i])
                collected_length += len(lines[i]) + 1  # +1 for newline
                i += 1

            # Try to parse the collected JSON
            json_str = '\n'.join(json_content).strip()
            if json_str:
                try:
                    parsed = json.loads(json_str)
                    chunks.append(parsed)
                except json.JSONDecodeError:
                    # Store as raw string if not valid JSON
                    chunks.append(json_str)
        else:
            # Not a length prefix, try to parse as JSON directly
            try:
                parsed = json.loads(line)
                chunks.append(parsed)
            except json.JSONDecodeError:
                pass
            i += 1

    if chunks:
        return json.dumps(chunks, ensure_ascii=False, separators=(',', ':'))

    return text


def _normalize_sse(content: bytes) -> str:
    """
    Normalize SSE stream by extracting data payloads.
    Handles LLM streaming responses (ChatGPT, Claude, etc.)
    """
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        return _to_string(content)

    lines = text.split('\n')
    extracted: list[str] = []

    for line in lines:
        print(line)
        line = line.strip()
        if not line or line.startswith(':'):
            continue
        if line == 'data: [DONE]':
            continue
        if line.startswith('event:'):
            encoding_type = line[6:].strip()
            # Future: handle specific event types if needed
            continue
        if line.startswith('data:'):
            data = line[5:].strip()
            if data:
                try:
                    obj = json.loads(data)
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    pass
                extracted.append(data)

    if extracted:
        return ''.join(extracted), encoding_type

    return text, encoding_type


def _is_msgpack(content: bytes) -> bool:
    """Detect MessagePack format via magic bytes."""
    if len(content) < 1:
        return False
    return content[0] in MSGPACK_MARKERS


def _decode_msgpack(content: bytes) -> str | None:
    """Decode MessagePack to JSON string."""
    try:
        import msgpack
        obj = msgpack.unpackb(content, raw=False)
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    except ImportError:
        return None
    except Exception:
        return None


def _decode_layers(content: bytes) -> bytes:
    """Attempt to decode nested encodings up to MAX_DECODE_LAYERS."""
    current = content

    for _ in range(MAX_DECODE_LAYERS):
        encoding = _detect_encoding(current)
        if not encoding:
            break

        try:
            decoded = _apply_decoder(current, encoding)
            if decoded == current:
                break
            current = decoded
        except Exception:
            break

    return current


def _detect_encoding(content: bytes) -> str | None:
    """Detect encoding type using magic bytes and heuristics."""
    if len(content) < 2:
        return None

    # Compression magic bytes (most reliable)
    if content[:2] == GZIP_MAGIC:
        return 'gzip'
    if len(content) >= 4 and content[:4] == ZSTD_MAGIC:
        return 'zstd'
    if content[:2] in ZLIB_PREFIXES:
        return 'deflate'

    # URL encoding
    if b'%' in content and URL_ENCODED_PATTERN.search(content):
        try:
            content.decode('ascii')
            return 'url'
        except (UnicodeDecodeError, AttributeError):
            pass

    # Base64 (check last - many false positives)
    if len(content) >= MIN_BASE64_LENGTH:
        try:
            content.decode('ascii')
            stripped = content.strip()
            if len(stripped) % 4 <= 2:
                if BASE64_PATTERN.match(stripped):
                    try:
                        decoded = base64.b64decode(stripped)
                        if len(decoded) > 0:
                            return 'base64'
                    except Exception:
                        pass
                elif BASE64_URL_PATTERN.match(stripped):
                    try:
                        padded = stripped + b'=' * (4 - len(stripped) % 4) if len(stripped) % 4 else stripped
                        decoded = base64.urlsafe_b64decode(padded)
                        if len(decoded) > 0:
                            return 'base64_url'
                    except Exception:
                        pass
        except (UnicodeDecodeError, AttributeError):
            pass

    return None


def _apply_decoder(content: bytes, encoding: str) -> bytes:
    """Apply the appropriate decoder."""
    if encoding == 'gzip':
        return decode_gzip(content)
    elif encoding == 'deflate':
        return decode_deflate(content)
    elif encoding == 'zstd':
        return decode_zstd(content)
    elif encoding == 'base64':
        return _decode_base64(content)
    elif encoding == 'base64_url':
        return _decode_base64_url(content)
    elif encoding == 'url':
        return _decode_url(content)
    return content


def _decode_base64(content: bytes) -> bytes:
    """Decode standard base64."""
    text = content.decode('ascii').strip()
    padding = 4 - (len(text) % 4)
    if padding != 4:
        text += '=' * padding
    return base64.b64decode(text)


def _decode_base64_url(content: bytes) -> bytes:
    """Decode URL-safe base64."""
    text = content.decode('ascii').strip()
    padding = 4 - (len(text) % 4)
    if padding != 4:
        text += '=' * padding
    return base64.urlsafe_b64decode(text)


def _decode_url(content: bytes) -> bytes:
    """Decode URL percent-encoding."""
    text = content.decode('utf-8')
    return urllib.parse.unquote(text).encode('utf-8')
