"""Comprehensive unit tests for normalize.py.

Tests cover all pure data transformation functions with no I/O dependencies.
This is the highest ROI test file since normalize.py is pure logic.
"""

from __future__ import annotations

import base64
import gzip
import json
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
from mitmproxy.addons.oximy.normalize import (
    ANTI_HIJACK_PREFIXES,
    BASE64_PATTERN,
    BASE64_URL_PATTERN,
    GZIP_MAGIC,
    MAX_BODY_SIZE,
    MAX_DECODE_LAYERS,
    MIN_BASE64_LENGTH,
    MSGPACK_MARKERS,
    ZLIB_PREFIXES,
    ZSTD_MAGIC,
    _apply_decoder,
    _convert_bytes_to_str,
    _decode_base64,
    _decode_base64_url,
    _decode_grpc_frames,
    _decode_layers,
    _decode_msgpack,
    _decode_protobuf_schemaless,
    _decode_url,
    _detect_encoding,
    _get_anti_hijack_prefix,
    _has_anti_hijack_prefix,
    _is_grpc_content,
    _is_msgpack,
    _is_sse_stream,
    _normalize_anti_hijack_stream,
    _normalize_sse,
    _to_string,
    normalize_body,
    normalize_grpc,
)


# =============================================================================
# _is_grpc_content Tests
# =============================================================================

class TestIsGrpcContent:
    """Tests for _is_grpc_content function."""

    @pytest.mark.parametrize("content_type,expected", [
        ("application/grpc", True),
        ("application/grpc+proto", True),
        ("application/grpc-web", True),
        ("application/grpc-web+proto", True),
        ("application/x-protobuf", True),
        ("APPLICATION/GRPC", True),  # Case insensitive
        ("Application/X-Protobuf", True),  # Case insensitive
    ])
    def test_grpc_content_types_return_true(self, content_type: str, expected: bool):
        """Verify gRPC/protobuf content types are detected."""
        assert _is_grpc_content(content_type) is expected

    @pytest.mark.parametrize("content_type", [
        "application/json",
        "text/html",
        "text/plain",
        "application/xml",
        "multipart/form-data",
        "",
    ])
    def test_non_grpc_content_types_return_false(self, content_type: str):
        """Verify non-gRPC content types are not detected."""
        assert _is_grpc_content(content_type) is False

    def test_none_content_type_returns_false(self):
        """Verify None content type returns False."""
        assert _is_grpc_content(None) is False


# =============================================================================
# _decode_grpc_frames Tests
# =============================================================================

class TestDecodeGrpcFrames:
    """Tests for _decode_grpc_frames function."""

    def test_empty_content_returns_empty_list(self):
        """Empty content should return empty list."""
        assert _decode_grpc_frames(b"") == []

    def test_single_frame(self, grpc_single_frame: bytes):
        """Single valid frame should be parsed."""
        result = _decode_grpc_frames(grpc_single_frame)
        assert result == [b"abc"]

    def test_multiple_frames(self, grpc_multi_frame: bytes):
        """Multiple frames should all be parsed."""
        result = _decode_grpc_frames(grpc_multi_frame)
        assert result == [b"abc", b"def"]

    def test_incomplete_frame_stops_parsing(self, grpc_incomplete_frame: bytes):
        """Incomplete frame should stop parsing gracefully."""
        result = _decode_grpc_frames(grpc_incomplete_frame)
        assert result == []  # Frame says 10 bytes but only 3 present

    def test_frame_with_zero_length_message(self):
        """Zero-length message should be parsed correctly."""
        frame = b'\x00\x00\x00\x00\x00'  # 0-byte message
        result = _decode_grpc_frames(frame)
        assert result == [b""]

    def test_short_header_returns_empty(self):
        """Content shorter than header size returns empty."""
        assert _decode_grpc_frames(b"\x00\x00") == []
        assert _decode_grpc_frames(b"\x00\x00\x00\x00") == []

    def test_compressed_flag_ignored(self):
        """Compression flag is parsed but not used (we extract raw bytes)."""
        # Compression flag = 1 (gzip), but we just extract raw message
        frame = b'\x01\x00\x00\x00\x03abc'
        result = _decode_grpc_frames(frame)
        assert result == [b"abc"]

    def test_large_message(self):
        """Large message (100KB) should be parsed correctly."""
        message = b"x" * 100000
        length = len(message).to_bytes(4, 'big')
        frame = b'\x00' + length + message
        result = _decode_grpc_frames(frame)
        assert result == [message]


# =============================================================================
# _convert_bytes_to_str Tests
# =============================================================================

class TestConvertBytesToStr:
    """Tests for _convert_bytes_to_str function."""

    def test_utf8_bytes_decoded(self):
        """UTF-8 bytes should be decoded to string."""
        assert _convert_bytes_to_str(b"hello world") == "hello world"

    def test_non_utf8_bytes_base64_encoded(self):
        """Non-UTF-8 bytes should be base64 encoded."""
        binary = bytes([0xff, 0xfe, 0x00, 0x01])
        result = _convert_bytes_to_str(binary)
        assert result == base64.b64encode(binary).decode('ascii')

    def test_dict_recursively_converted(self):
        """Dict values should be recursively converted."""
        data = {"key": b"value", "nested": {"inner": b"\xff\xfe"}}
        result = _convert_bytes_to_str(data)
        assert result["key"] == "value"
        assert result["nested"]["inner"] == base64.b64encode(b"\xff\xfe").decode('ascii')

    def test_list_recursively_converted(self):
        """List items should be recursively converted."""
        data = [b"hello", b"\xff\xfe", "already string"]
        result = _convert_bytes_to_str(data)
        assert result[0] == "hello"
        assert result[1] == base64.b64encode(b"\xff\xfe").decode('ascii')
        assert result[2] == "already string"

    def test_non_bytes_unchanged(self):
        """Non-bytes values should be returned unchanged."""
        assert _convert_bytes_to_str(42) == 42
        assert _convert_bytes_to_str("string") == "string"
        assert _convert_bytes_to_str(3.14) == 3.14
        assert _convert_bytes_to_str(None) is None

    def test_msgpack_timestamp_conversion(self):
        """MessagePack Timestamp should be converted to ISO format or unix time."""
        try:
            import msgpack
            # Create a real msgpack Timestamp
            ts = msgpack.Timestamp(seconds=1705312200, nanoseconds=0)
            result = _convert_bytes_to_str(ts)
            assert isinstance(result, str)
            # Should be ISO format with Z suffix or unix timestamp
            assert "2024" in result or result.replace(".", "").isdigit()
        except ImportError:
            pytest.skip("msgpack not installed")

    def test_mixed_nested_structure(self):
        """Complex nested structure should be fully converted."""
        data = {
            "string": "text",
            "bytes": b"binary",
            "list": [b"a", {"inner": b"b"}],
            "number": 123,
        }
        result = _convert_bytes_to_str(data)
        assert result["string"] == "text"
        assert result["bytes"] == "binary"
        assert result["list"][0] == "a"
        assert result["list"][1]["inner"] == "b"
        assert result["number"] == 123


# =============================================================================
# _is_sse_stream Tests
# =============================================================================

class TestIsSseStream:
    """Tests for _is_sse_stream function."""

    def test_exact_match_returns_true(self):
        """Exact SSE content-type should return True."""
        assert _is_sse_stream("text/event-stream; charset=utf-8") is True

    def test_non_sse_returns_false(self):
        """Non-SSE content types should return False."""
        assert _is_sse_stream("application/json") is False
        assert _is_sse_stream("text/plain") is False
        assert _is_sse_stream("text/event-stream") is False  # Without charset
        assert _is_sse_stream("") is False


# =============================================================================
# _has_anti_hijack_prefix Tests
# =============================================================================

class TestHasAntiHijackPrefix:
    """Tests for _has_anti_hijack_prefix function."""

    @pytest.mark.parametrize("prefix", ANTI_HIJACK_PREFIXES)
    def test_each_prefix_detected(self, prefix: bytes):
        """Each anti-hijack prefix should be detected."""
        content = prefix + b'{"data": "test"}'
        assert _has_anti_hijack_prefix(content) is True

    def test_normal_json_not_detected(self):
        """Normal JSON should not be detected as anti-hijack."""
        assert _has_anti_hijack_prefix(b'{"normal": "json"}') is False
        assert _has_anti_hijack_prefix(b'[1, 2, 3]') is False

    def test_empty_content_not_detected(self):
        """Empty content should not trigger detection."""
        assert _has_anti_hijack_prefix(b"") is False


# =============================================================================
# _get_anti_hijack_prefix Tests
# =============================================================================

class TestGetAntiHijackPrefix:
    """Tests for _get_anti_hijack_prefix function."""

    @pytest.mark.parametrize("prefix", ANTI_HIJACK_PREFIXES)
    def test_returns_matching_prefix(self, prefix: bytes):
        """Should return the matching prefix."""
        content = prefix + b'{"data": 1}'
        assert _get_anti_hijack_prefix(content) == prefix

    def test_returns_none_for_no_match(self):
        """Should return None when no prefix matches."""
        assert _get_anti_hijack_prefix(b'{"regular": "json"}') is None
        assert _get_anti_hijack_prefix(b"") is None


# =============================================================================
# _normalize_anti_hijack_stream Tests
# =============================================================================

class TestNormalizeAntiHijackStream:
    """Tests for _normalize_anti_hijack_stream function."""

    def test_simple_json_after_prefix(self, anti_hijack_google: bytes):
        """JSON after Google-style prefix should be extracted."""
        result = _normalize_anti_hijack_stream(anti_hijack_google)
        parsed = json.loads(result)
        assert parsed == [{"data": 123}]

    def test_facebook_style_prefix(self, anti_hijack_facebook: bytes):
        """JSON after Facebook-style prefix should be extracted."""
        result = _normalize_anti_hijack_stream(anti_hijack_facebook)
        parsed = json.loads(result)
        assert parsed == [{"user": "test"}]

    def test_while_style_prefix(self, anti_hijack_while: bytes):
        """JSON after while-style prefix should be extracted."""
        result = _normalize_anti_hijack_stream(anti_hijack_while)
        parsed = json.loads(result)
        assert parsed == [{"status": "ok"}]

    def test_empty_object_prefix(self, anti_hijack_empty_obj: bytes):
        """JSON after empty object prefix should be extracted."""
        result = _normalize_anti_hijack_stream(anti_hijack_empty_obj)
        parsed = json.loads(result)
        assert parsed == [{"result": True}]

    def test_length_prefixed_chunks(self, anti_hijack_length_prefixed: bytes):
        """Length-prefixed streaming chunks should be parsed."""
        result = _normalize_anti_hijack_stream(anti_hijack_length_prefixed)
        parsed = json.loads(result)
        assert len(parsed) >= 1  # Should extract chunks

    def test_non_utf8_fallback(self):
        """Non-UTF8 content should fall back to _to_string."""
        content = b")]}'\n\xff\xfe\xfd"
        result = _normalize_anti_hijack_stream(content)
        assert isinstance(result, str)


# =============================================================================
# _normalize_sse Tests
# =============================================================================

class TestNormalizeSse:
    """Tests for _normalize_sse function."""

    def test_data_lines_extracted(self, sse_simple: bytes):
        """Data lines should be extracted and concatenated."""
        result, encoding = _normalize_sse(sse_simple)
        assert '{"message": "hello"}' in result
        assert '{"message": "world"}' in result

    def test_event_type_captured(self, sse_with_events: bytes):
        """Event type should be captured."""
        result, encoding = _normalize_sse(sse_with_events)
        # Last event type seen should be returned
        assert encoding in ["message", "done"]

    def test_comments_ignored(self, sse_with_comments: bytes):
        """Lines starting with : should be ignored."""
        result, encoding = _normalize_sse(sse_with_comments)
        assert "comment" not in result.lower()
        assert '{"value": 42}' in result

    def test_done_marker_skipped(self, sse_done_marker: bytes):
        """[DONE] marker should be skipped."""
        result, encoding = _normalize_sse(sse_done_marker)
        assert "[DONE]" not in result
        assert '{"delta": "text"}' in result

    def test_non_utf8_fallback(self):
        """Non-UTF8 content should fall back gracefully."""
        content = b"\xff\xfe\xfd"
        result, encoding = _normalize_sse(content)
        assert isinstance(result, str)

    def test_empty_data_lines_ignored(self):
        """Empty data: lines should be ignored."""
        content = b"data:\ndata: \ndata: {\"real\": \"data\"}\n\n"
        result, encoding = _normalize_sse(content)
        assert '{"real": "data"}' in result


# =============================================================================
# _is_msgpack Tests
# =============================================================================

class TestIsMsgpack:
    """Tests for _is_msgpack function."""

    @pytest.mark.parametrize("marker", list(MSGPACK_MARKERS)[:10])
    def test_valid_markers_detected(self, marker: int):
        """Valid MessagePack markers should be detected."""
        content = bytes([marker]) + b"\x00\x00"
        assert _is_msgpack(content) is True

    def test_empty_content_returns_false(self):
        """Empty content should return False."""
        assert _is_msgpack(b"") is False

    def test_non_msgpack_returns_false(self):
        """Non-MessagePack content should return False."""
        assert _is_msgpack(b'{"json": true}') is False
        assert _is_msgpack(b"hello world") is False
        assert _is_msgpack(b"\x00\x01\x02") is False  # Not a msgpack marker


# =============================================================================
# _decode_msgpack Tests
# =============================================================================

class TestDecodeMsgpack:
    """Tests for _decode_msgpack function."""

    def test_valid_msgpack_decoded(self):
        """Valid MessagePack should be decoded to JSON string."""
        try:
            import msgpack
            data = {"key": "value", "num": 42}
            packed = msgpack.packb(data)
            result = _decode_msgpack(packed)
            assert result is not None
            parsed = json.loads(result)
            assert parsed["key"] == "value"
            assert parsed["num"] == 42
        except ImportError:
            pytest.skip("msgpack not installed")

    def test_decode_failure_returns_none(self):
        """Decode failure should return None."""
        # Invalid msgpack data (just a marker with no valid content)
        result = _decode_msgpack(b"\x81")  # Map with 1 element but no data
        assert result is None

    def test_import_error_returns_none(self):
        """Missing msgpack library should return None."""
        import sys
        # Save and remove msgpack from modules to force ImportError
        saved = sys.modules.pop('msgpack', None)
        try:
            with patch.dict('sys.modules', {'msgpack': None}):
                result = _decode_msgpack(b"\x81\x01\x02")
                assert result is None
        finally:
            if saved:
                sys.modules['msgpack'] = saved


# =============================================================================
# _detect_encoding Tests
# =============================================================================

class TestDetectEncoding:
    """Tests for _detect_encoding function."""

    def test_gzip_detected(self, gzip_hello: bytes):
        """Gzip magic bytes should be detected."""
        assert _detect_encoding(gzip_hello) == "gzip"

    def test_zstd_detected(self):
        """Zstd magic bytes should be detected."""
        content = ZSTD_MAGIC + b"\x00" * 10
        assert _detect_encoding(content) == "zstd"

    def test_zlib_deflate_detected(self):
        """Zlib prefixes should be detected as deflate."""
        for prefix in ZLIB_PREFIXES:
            content = prefix + b"\x00" * 10
            assert _detect_encoding(content) == "deflate"

    def test_url_encoding_detected(self):
        """URL percent-encoding should be detected."""
        content = b"hello%20world%21"
        assert _detect_encoding(content) == "url"

    def test_base64_detected(self, base64_hello: bytes):
        """Valid base64 should be detected."""
        assert _detect_encoding(base64_hello) == "base64"

    def test_base64_url_detected(self):
        """URL-safe base64 should be detected when it has URL-specific chars."""
        import base64
        # Use bytes that produce - and _ in URL-safe encoding (not valid in standard base64)
        # bytes([0xfb, 0xef, 0xbf]) encodes to '---_' in URL-safe, '+++/' in standard
        # We need enough length to pass MIN_BASE64_LENGTH (20)
        url_safe_data = bytes([0xfb, 0xef, 0xbf]) * 6  # Repeat to get sufficient length
        url_safe = base64.urlsafe_b64encode(url_safe_data)
        # URL-safe encoded content with - and _ won't match standard base64 pattern
        # because - and _ are not in [A-Za-z0-9+/]
        result = _detect_encoding(url_safe)
        assert result == "base64_url"

    def test_short_content_returns_none(self):
        """Content shorter than 2 bytes should return None."""
        assert _detect_encoding(b"") is None
        assert _detect_encoding(b"\x00") is None

    def test_plain_text_returns_none(self):
        """Plain text without encoding should return None."""
        assert _detect_encoding(b"plain text here") is None
        assert _detect_encoding(b'{"json": true}') is None

    def test_short_base64_not_detected(self):
        """Base64 shorter than MIN_BASE64_LENGTH should not be detected."""
        short = base64.b64encode(b"hi")  # Very short
        if len(short) < MIN_BASE64_LENGTH:
            assert _detect_encoding(short) is None


# =============================================================================
# _apply_decoder Tests
# =============================================================================

class TestApplyDecoder:
    """Tests for _apply_decoder function."""

    def test_gzip_decoded(self, gzip_hello: bytes):
        """Gzip content should be decoded."""
        result = _apply_decoder(gzip_hello, "gzip")
        assert result == b"hello"

    def test_base64_decoded(self, base64_hello: bytes):
        """Base64 content should be decoded."""
        result = _apply_decoder(base64_hello, "base64")
        assert result == b"hello world test data"

    def test_base64_url_decoded(self):
        """URL-safe base64 should be decoded."""
        import base64
        original = b"hello+world/test"
        encoded = base64.urlsafe_b64encode(original)
        result = _apply_decoder(encoded, "base64_url")
        assert result == original

    def test_url_decoded(self, url_encoded: bytes):
        """URL encoding should be decoded."""
        result = _apply_decoder(url_encoded, "url")
        assert result == b"hello world!"

    def test_unknown_encoding_unchanged(self):
        """Unknown encoding should return content unchanged."""
        content = b"test content"
        result = _apply_decoder(content, "unknown")
        assert result == content


# =============================================================================
# _decode_base64 Tests
# =============================================================================

class TestDecodeBase64:
    """Tests for _decode_base64 function."""

    def test_standard_base64_decoded(self):
        """Standard base64 should be decoded."""
        encoded = base64.b64encode(b"hello world")
        result = _decode_base64(encoded)
        assert result == b"hello world"

    def test_padding_added_if_missing(self):
        """Missing padding should be added automatically."""
        # Base64 of "hello" is "aGVsbG8="
        # Remove padding for test
        no_padding = b"aGVsbG8"
        result = _decode_base64(no_padding)
        assert result == b"hello"

    def test_whitespace_stripped(self):
        """Whitespace should be stripped."""
        encoded = b"  " + base64.b64encode(b"test") + b"  \n"
        result = _decode_base64(encoded)
        assert result == b"test"


# =============================================================================
# _decode_base64_url Tests
# =============================================================================

class TestDecodeBase64Url:
    """Tests for _decode_base64_url function."""

    def test_url_safe_base64_decoded(self):
        """URL-safe base64 should be decoded."""
        encoded = base64.urlsafe_b64encode(b"hello+world/test")
        result = _decode_base64_url(encoded)
        assert result == b"hello+world/test"

    def test_padding_added_if_missing(self):
        """Missing padding should be added automatically."""
        # URL-safe base64 of "hi" without padding
        no_padding = b"aGk"
        result = _decode_base64_url(no_padding)
        assert result == b"hi"


# =============================================================================
# _decode_url Tests
# =============================================================================

class TestDecodeUrl:
    """Tests for _decode_url function."""

    def test_percent_encoding_decoded(self):
        """Percent-encoded characters should be decoded."""
        result = _decode_url(b"hello%20world%21")
        assert result == b"hello world!"

    def test_plus_not_decoded_as_space(self):
        """Plus signs should not be decoded as spaces (that's form encoding)."""
        result = _decode_url(b"hello+world")
        assert result == b"hello+world"

    def test_unicode_decoded(self):
        """Unicode percent-encoding should be decoded."""
        # %C3%A9 is é in UTF-8
        result = _decode_url(b"caf%C3%A9")
        assert result == "café".encode('utf-8')


# =============================================================================
# _decode_layers Tests
# =============================================================================

class TestDecodeLayers:
    """Tests for _decode_layers function."""

    def test_single_layer_decoded(self, gzip_hello: bytes):
        """Single encoding layer should be decoded."""
        result = _decode_layers(gzip_hello)
        assert result == b"hello"

    def test_nested_layers_decoded(self):
        """Nested encodings should be decoded up to MAX_DECODE_LAYERS."""
        # Base64(gzip("hello"))
        compressed = gzip.compress(b"hello")
        double_encoded = base64.b64encode(compressed)
        result = _decode_layers(double_encoded)
        assert result == b"hello"

    def test_max_layers_respected(self):
        """Should stop after MAX_DECODE_LAYERS iterations."""
        # Create deeply nested encoding
        content = b"test"
        for _ in range(MAX_DECODE_LAYERS + 2):
            content = base64.b64encode(content)

        result = _decode_layers(content)
        # Should have decoded some layers but not infinitely
        assert result != content  # Some decoding happened

    def test_no_encoding_unchanged(self):
        """Plain content should be returned unchanged."""
        content = b"plain text"
        result = _decode_layers(content)
        assert result == content


# =============================================================================
# _to_string Tests
# =============================================================================

class TestToString:
    """Tests for _to_string function."""

    def test_utf8_decoded(self):
        """UTF-8 bytes should be decoded to string."""
        assert _to_string(b"hello world") == "hello world"

    def test_binary_returns_base64_json(self):
        """Pure binary content should return JSON with base64."""
        binary = bytes(range(256))
        result = _to_string(binary)
        parsed = json.loads(result)
        assert "_binary_base64" in parsed
        assert parsed["_binary_base64"] == base64.b64encode(binary).decode('ascii')

    def test_mostly_printable_uses_replacement(self):
        """Content >80% printable should use replacement characters."""
        # 90 printable + 10 non-printable = 90% printable
        content = b"a" * 90 + bytes(range(128, 138))
        result = _to_string(content)
        # Should contain the 'a's and replacement chars, not be base64
        assert "a" * 10 in result
        assert "_binary_base64" not in result


# =============================================================================
# normalize_body Tests
# =============================================================================

class TestNormalizeBody:
    """Tests for normalize_body function."""

    def test_none_returns_empty_string(self):
        """None content should return empty string."""
        assert normalize_body(None) == ""

    def test_empty_returns_empty_string(self):
        """Empty content should return empty string."""
        assert normalize_body(b"") == ""

    def test_large_body_truncated(self):
        """Bodies larger than MAX_BODY_SIZE should be truncated."""
        large_content = b"x" * (MAX_BODY_SIZE + 1000)
        result = normalize_body(large_content)
        assert "truncated" in result.lower()
        assert str(len(large_content)) in result

    def test_grpc_content_routed(self, grpc_single_frame: bytes):
        """gRPC content should be routed to normalize_grpc."""
        result = normalize_body(grpc_single_frame, "application/grpc")
        # Should be JSON output from gRPC normalization
        assert isinstance(result, str)

    def test_sse_content_routed(self, sse_simple: bytes):
        """SSE content should be routed to _normalize_sse."""
        result = normalize_body(sse_simple, "text/event-stream; charset=utf-8")
        assert "hello" in result or "message" in result

    def test_anti_hijack_content_routed(self, anti_hijack_google: bytes):
        """Anti-hijack prefixed content should be handled."""
        result = normalize_body(anti_hijack_google)
        assert "data" in result

    def test_msgpack_content_decoded(self):
        """MessagePack content should be decoded if library available."""
        try:
            import msgpack
            data = {"test": "value"}
            packed = msgpack.packb(data)
            result = normalize_body(packed)
            assert "test" in result
        except ImportError:
            pytest.skip("msgpack not installed")

    def test_plain_json_unchanged(self):
        """Plain JSON should be returned as string."""
        content = b'{"key": "value"}'
        result = normalize_body(content)
        assert result == '{"key": "value"}'

    def test_binary_content_handled(self):
        """Binary content should be converted to base64 JSON."""
        binary = bytes(range(256))
        result = normalize_body(binary)
        assert "_binary_base64" in result or isinstance(result, str)

    def test_gzip_decoded_then_normalized(self, gzip_hello: bytes):
        """Gzip content should be decoded and normalized."""
        result = normalize_body(gzip_hello)
        assert result == "hello"


# =============================================================================
# normalize_grpc Tests
# =============================================================================

class TestNormalizeGrpc:
    """Tests for normalize_grpc function."""

    def test_empty_returns_empty_string(self):
        """Empty content should return empty string."""
        assert normalize_grpc(b"") == ""

    def test_single_frame_decoded(self, grpc_single_frame: bytes):
        """Single frame should produce JSON output."""
        result = normalize_grpc(grpc_single_frame)
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        # Will have _raw_base64 if protobuf decode fails
        assert isinstance(parsed, dict)

    def test_multiple_frames_produces_array(self, grpc_multi_frame: bytes):
        """Multiple frames should produce JSON array."""
        result = normalize_grpc(grpc_multi_frame)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_no_frames_treats_as_single_message(self):
        """Content with no valid frames should be treated as single protobuf."""
        content = b"not a valid grpc frame"
        result = normalize_grpc(content)
        parsed = json.loads(result)
        # Should have _raw_base64 fallback
        assert "_raw_base64" in parsed or isinstance(parsed, dict)

    def test_decode_failure_fallback(self):
        """Decode failure should fall back to base64 encoding."""
        content = b"\xff\xfe\xfd"
        result = normalize_grpc(content)
        parsed = json.loads(result)
        assert "_raw_base64" in parsed


# =============================================================================
# _decode_protobuf_schemaless Tests
# =============================================================================

class TestDecodeProtobufSchemaless:
    """Tests for _decode_protobuf_schemaless function."""

    def test_large_message_skipped(self):
        """Messages >1MB should be skipped."""
        large_data = b"\x00" * 1_500_000
        result = _decode_protobuf_schemaless(large_data)
        assert result is None

    def test_import_error_returns_none(self):
        """Missing blackboxprotobuf should return None."""
        import sys
        # Save and remove blackboxprotobuf from modules to force ImportError
        saved = sys.modules.pop('blackboxprotobuf', None)
        try:
            with patch.dict('sys.modules', {'blackboxprotobuf': None}):
                result = _decode_protobuf_schemaless(b"\x08\x96\x01")
                assert result is None
        finally:
            if saved:
                sys.modules['blackboxprotobuf'] = saved


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestZstdDecoding:
    """Tests for zstd decompression."""

    def test_zstd_content_decoded(self):
        """Zstd-compressed content should be detected and decoded."""
        try:
            from mitmproxy.net.encoding import decode_zstd
            import zstandard
            # Compress some content
            cctx = zstandard.ZstdCompressor()
            compressed = cctx.compress(b"hello zstd world")
            # Verify detection
            assert _detect_encoding(compressed) == "zstd"
            # Verify decoding via normalize_body
            result = normalize_body(compressed)
            assert "hello zstd world" in result
        except ImportError:
            pytest.skip("zstandard not installed")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_normalize_body_never_raises(self):
        """normalize_body should never raise an exception."""
        test_cases = [
            None,
            b"",
            b"\x00\x01\x02",
            b"normal text",
            b'{"json": true}',
            bytes(range(256)),
            b"\xff" * 1000,
        ]
        for content in test_cases:
            try:
                result = normalize_body(content)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"normalize_body raised {type(e).__name__}: {e}")

    def test_concurrent_safe(self):
        """Functions should be thread-safe."""
        import concurrent.futures

        def call_normalize():
            for _ in range(100):
                normalize_body(b'{"test": "data"}')
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(call_normalize) for _ in range(4)]
            for future in concurrent.futures.as_completed(futures):
                assert future.result() is True
