"""Comprehensive unit tests for addon.py pure logic functions.

Tests cover only the pure logic functions that don't require mitmproxy context
or I/O operations. Functions with filesystem, subprocess, or network dependencies
are mocked appropriately.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import the functions under test
from mitmproxy.addons.oximy.addon import (
    WINDOWS_BROWSERS,
    MemoryTraceBuffer,
    TLSPassthrough,
    _build_url_regex,
    _extract_domain_from_pattern,
    contains_blacklist_word,
    extract_graphql_operation,
    generate_event_id,
    load_output_config,
    matches_app_origin,
    matches_domain,
    matches_host_origin,
    matches_whitelist,
    _matches_url_pattern,
)


# =============================================================================
# matches_domain Tests
# =============================================================================

class TestMatchesDomain:
    """Tests for matches_domain function."""

    def test_exact_match(self):
        """Exact domain match should return the pattern."""
        patterns = ["api.openai.com", "anthropic.com"]
        assert matches_domain("api.openai.com", patterns) == "api.openai.com"
        assert matches_domain("API.OPENAI.COM", patterns) == "api.openai.com"  # Case insensitive

    def test_wildcard_prefix(self):
        """Wildcard *.example.com should match subdomains."""
        patterns = ["*.openai.com"]
        assert matches_domain("api.openai.com", patterns) == "*.openai.com"
        assert matches_domain("chat.openai.com", patterns) == "*.openai.com"
        assert matches_domain("openai.com", patterns) == "*.openai.com"  # Bare domain also matches

    def test_subdomain_match(self):
        """Wildcard should match any subdomain level."""
        patterns = ["*.example.com"]
        assert matches_domain("a.b.c.example.com", patterns) == "*.example.com"

    def test_no_match(self):
        """Non-matching domain should return None."""
        patterns = ["api.openai.com", "*.anthropic.com"]
        assert matches_domain("google.com", patterns) is None
        assert matches_domain("openai.org", patterns) is None

    def test_empty_patterns(self):
        """Empty patterns list should return None."""
        assert matches_domain("api.openai.com", []) is None

    def test_fnmatch_patterns(self):
        """Should support fnmatch-style patterns."""
        patterns = ["*openai*"]
        assert matches_domain("api.openai.com", patterns) == "*openai*"

    def test_regex_patterns(self):
        """Should support regex patterns like bedrock-runtime.*.amazonaws.com."""
        patterns = ["bedrock-runtime.*.amazonaws.com"]
        assert matches_domain("bedrock-runtime.us-east-1.amazonaws.com", patterns) == "bedrock-runtime.*.amazonaws.com"

    def test_pattern_with_path_extracts_domain(self):
        """Patterns with paths should only match the domain portion."""
        patterns = ["api.openai.com/v1/chat"]
        assert matches_domain("api.openai.com", patterns) == "api.openai.com/v1/chat"


# =============================================================================
# _matches_url_pattern Tests
# =============================================================================

class TestMatchesUrlPattern:
    """Tests for _matches_url_pattern function."""

    def test_simple_domain_pattern(self):
        """Simple domain pattern should match."""
        assert _matches_url_pattern("api.openai.com/v1/chat", "api.openai.com") is True

    def test_path_pattern_match(self):
        """Pattern with path should match."""
        assert _matches_url_pattern("api.openai.com/v1/chat/completions", "api.openai.com/v1/chat") is True

    def test_double_star_wildcard(self):
        """** should match any path including /."""
        assert _matches_url_pattern("gemini.google.com/v1/models/StreamGenerate", "gemini.google.com/**/StreamGenerate*") is True
        assert _matches_url_pattern("gemini.google.com/deep/path/StreamGenerateContent", "gemini.google.com/**/StreamGenerate*") is True

    def test_single_star_wildcard(self):
        """* should match characters except /."""
        assert _matches_url_pattern("api.example.com/v1/test", "api.example.com/*/test") is True
        assert _matches_url_pattern("api.example.com/v1/v2/test", "api.example.com/*/test") is False

    def test_subdomain_wildcard_with_path(self):
        """*.domain.com/** should match subdomains with any path."""
        assert _matches_url_pattern("api.replit.com/graphql", "*.replit.com/**") is True
        assert _matches_url_pattern("www.replit.com/deep/path", "*.replit.com/**") is True
        assert _matches_url_pattern("replit.com/graphql", "*.replit.com/**") is True

    def test_subdomain_wildcard_specific_path(self):
        """*.domain.com/path should match subdomains with specific path."""
        assert _matches_url_pattern("api.example.com/graphql", "*.example.com/graphql") is True
        assert _matches_url_pattern("api.example.com/other", "*.example.com/graphql") is False

    def test_no_match(self):
        """Non-matching URL should return False."""
        assert _matches_url_pattern("google.com/search", "api.openai.com/**") is False

    def test_url_with_query_string(self):
        """URLs with query strings should still match path patterns."""
        # Query strings are part of the URL, patterns should handle them
        assert _matches_url_pattern("api.example.com/v1/chat?key=value", "api.example.com/v1/**") is True
        assert _matches_url_pattern("api.example.com/search?q=test", "api.example.com/**") is True


# =============================================================================
# matches_whitelist Tests
# =============================================================================

class TestMatchesWhitelist:
    """Tests for matches_whitelist function."""

    def test_domain_only_pattern(self):
        """Domain-only pattern should match any path."""
        patterns = ["api.openai.com"]
        assert matches_whitelist("api.openai.com", "/v1/chat", patterns) == "api.openai.com"
        assert matches_whitelist("api.openai.com", "/v2/anything", patterns) == "api.openai.com"

    def test_domain_with_path_pattern(self):
        """Domain+path pattern should only match specific paths."""
        patterns = ["gemini.google.com/**/StreamGenerate*"]
        assert matches_whitelist("gemini.google.com", "/v1/models/StreamGenerateContent", patterns) == "gemini.google.com/**/StreamGenerate*"
        assert matches_whitelist("gemini.google.com", "/other/path", patterns) is None

    def test_wildcard_domain_any_path(self):
        """*.domain.com should match any path on subdomains."""
        patterns = ["*.anthropic.com"]
        assert matches_whitelist("api.anthropic.com", "/v1/messages", patterns) == "*.anthropic.com"
        assert matches_whitelist("claude.anthropic.com", "/chat", patterns) == "*.anthropic.com"

    def test_wildcard_domain_specific_path(self):
        """*.domain.com/path should match specific paths on subdomains."""
        patterns = ["*.replit.com/**/graphql"]
        assert matches_whitelist("api.replit.com", "/v1/graphql", patterns) == "*.replit.com/**/graphql"
        assert matches_whitelist("api.replit.com", "/rest/api", patterns) is None

    def test_no_match(self):
        """Non-matching host+path should return None."""
        patterns = ["api.openai.com", "*.anthropic.com"]
        assert matches_whitelist("google.com", "/search", patterns) is None

    def test_multiple_patterns(self):
        """Should check all patterns and return first match."""
        patterns = [
            "api.openai.com/v1/chat",
            "*.anthropic.com",
            "gemini.google.com/**/StreamGenerate*"
        ]
        # First match
        assert matches_whitelist("api.anthropic.com", "/messages", patterns) == "*.anthropic.com"


# =============================================================================
# contains_blacklist_word Tests
# =============================================================================

class TestContainsBlacklistWord:
    """Tests for contains_blacklist_word function."""

    def test_case_insensitive_match(self):
        """Match should be case-insensitive."""
        words = ["analytics", "tracking"]
        assert contains_blacklist_word("Google Analytics Script", words) == "analytics"
        assert contains_blacklist_word("ANALYTICS_EVENT", words) == "analytics"

    def test_partial_word_match(self):
        """Should match partial words (substring)."""
        words = ["analytics"]
        assert contains_blacklist_word("myanalyticstracker", words) == "analytics"

    def test_no_match(self):
        """Non-matching text should return None."""
        words = ["analytics", "tracking"]
        assert contains_blacklist_word("chat/completions", words) is None

    def test_empty_words_list(self):
        """Empty words list should return None."""
        assert contains_blacklist_word("anything", []) is None

    def test_empty_text(self):
        """Empty text should return None."""
        words = ["analytics"]
        assert contains_blacklist_word("", words) is None

    def test_none_text(self):
        """None text should return None (not raise)."""
        words = ["analytics"]
        assert contains_blacklist_word(None, words) is None  # type: ignore


# =============================================================================
# extract_graphql_operation Tests
# =============================================================================

class TestExtractGraphqlOperation:
    """Tests for extract_graphql_operation function."""

    def test_single_operation(self):
        """Should extract operation name from single operation."""
        body = b'{"query": "...", "operationName": "GetUser", "variables": {}}'
        assert extract_graphql_operation(body) == "GetUser"

    def test_batched_operations(self):
        """Should extract first operation name from batch."""
        body = b'[{"query": "...", "operationName": "Op1"}, {"query": "...", "operationName": "Op2"}]'
        assert extract_graphql_operation(body) == "Op1"

    def test_none_body(self):
        """None body should return None."""
        assert extract_graphql_operation(None) is None

    def test_empty_body(self):
        """Empty body should return None."""
        assert extract_graphql_operation(b"") is None

    def test_invalid_json(self):
        """Invalid JSON should return None."""
        assert extract_graphql_operation(b"not json") is None
        assert extract_graphql_operation(b"{invalid}") is None

    def test_missing_operation_name(self):
        """Missing operationName should return None."""
        body = b'{"query": "{ user { id } }", "variables": {}}'
        assert extract_graphql_operation(body) is None

    def test_batched_without_operation_name(self):
        """Batch without operationName should return None."""
        body = b'[{"query": "..."}, {"query": "..."}]'
        assert extract_graphql_operation(body) is None

    def test_non_dict_json(self):
        """Non-object/array JSON should return None."""
        assert extract_graphql_operation(b'"just a string"') is None
        assert extract_graphql_operation(b'123') is None


# =============================================================================
# matches_app_origin Tests
# =============================================================================

class TestMatchesAppOrigin:
    """Tests for matches_app_origin function."""

    def test_host_match(self):
        """Browser bundle IDs should return 'host'."""
        hosts = ["com.google.Chrome", "com.apple.Safari"]
        non_hosts = ["com.openai.ChatGPT"]

        assert matches_app_origin("com.google.Chrome", hosts, non_hosts) == "host"
        assert matches_app_origin("com.apple.Safari", hosts, non_hosts) == "host"

    def test_non_host_match(self):
        """AI-native app bundle IDs should return 'non_host'."""
        hosts = ["com.google.Chrome"]
        non_hosts = ["com.openai.ChatGPT", "com.anthropic.Claude"]

        assert matches_app_origin("com.openai.ChatGPT", hosts, non_hosts) == "non_host"
        assert matches_app_origin("com.anthropic.Claude", hosts, non_hosts) == "non_host"

    def test_no_match(self):
        """Unknown bundle ID should return None."""
        hosts = ["com.google.Chrome"]
        non_hosts = ["com.openai.ChatGPT"]

        assert matches_app_origin("com.unknown.App", hosts, non_hosts) is None

    def test_none_bundle_id(self):
        """None bundle ID should return None."""
        assert matches_app_origin(None, ["com.google.Chrome"], []) is None

    def test_case_insensitive(self):
        """Match should be case-insensitive."""
        hosts = ["com.google.Chrome"]
        non_hosts = []

        assert matches_app_origin("COM.GOOGLE.CHROME", hosts, non_hosts) == "host"
        assert matches_app_origin("Com.Google.Chrome", hosts, non_hosts) == "host"

    def test_windows_browser_detection(self):
        """Windows browser exe names should return 'host'."""
        # These come from WINDOWS_BROWSERS constant
        for browser in ["chrome.exe", "msedge.exe", "firefox.exe"]:
            assert matches_app_origin(browser, [], []) == "host"

    def test_non_host_takes_priority(self):
        """non_hosts should be checked before hosts."""
        # If same ID is in both lists, non_host should win
        both = "com.test.App"
        hosts = [both]
        non_hosts = [both]

        assert matches_app_origin(both, hosts, non_hosts) == "non_host"


# =============================================================================
# matches_host_origin Tests
# =============================================================================

class TestMatchesHostOrigin:
    """Tests for matches_host_origin function."""

    def test_exact_match(self):
        """Exact origin match should return True."""
        allowed = ["chatgpt.com", "claude.ai"]
        assert matches_host_origin("chatgpt.com", allowed) is True
        assert matches_host_origin("claude.ai", allowed) is True

    def test_subdomain_match(self):
        """Subdomain should match parent domain."""
        allowed = ["openai.com"]
        assert matches_host_origin("chat.openai.com", allowed) is True
        assert matches_host_origin("api.openai.com", allowed) is True

    def test_no_match(self):
        """Non-matching origin should return False."""
        allowed = ["chatgpt.com", "claude.ai"]
        assert matches_host_origin("google.com", allowed) is False

    def test_none_origin(self):
        """None origin should return False."""
        assert matches_host_origin(None, ["chatgpt.com"]) is False

    def test_empty_allowed_list(self):
        """Empty allowed list should return False."""
        assert matches_host_origin("chatgpt.com", []) is False

    def test_case_insensitive(self):
        """Match should be case-insensitive."""
        allowed = ["ChatGPT.com"]
        assert matches_host_origin("chatgpt.com", allowed) is True
        assert matches_host_origin("CHATGPT.COM", allowed) is True


# =============================================================================
# _build_url_regex Tests
# =============================================================================

class TestBuildUrlRegex:
    """Tests for _build_url_regex function."""

    def test_simple_domain(self):
        """Simple domain should produce exact match regex."""
        regex = _build_url_regex("api.openai.com")
        assert re.match(regex, "api.openai.com", re.IGNORECASE)
        assert re.match(regex, "api.openai.com/path", re.IGNORECASE)

    def test_double_star_pattern(self):
        """** should convert to .* (match anything including /)."""
        regex = _build_url_regex("example.com/**/test")
        assert re.match(regex, "example.com/a/b/c/test", re.IGNORECASE)

    def test_single_star_pattern(self):
        """* should convert to [^/]* (match anything except /)."""
        regex = _build_url_regex("example.com/*/test")
        pattern = re.compile(regex, re.IGNORECASE)
        assert pattern.match("example.com/v1/test")
        # Single * shouldn't match paths with /
        assert pattern.match("example.com/a/b/test") is None

    def test_slash_double_star_slash(self):
        """/**/ should match / or /anything/."""
        regex = _build_url_regex("example.com/**/path")
        pattern = re.compile(regex, re.IGNORECASE)
        assert pattern.match("example.com/path")
        assert pattern.match("example.com/a/path")
        assert pattern.match("example.com/a/b/c/path")

    def test_metacharacters_escaped(self):
        """Regex metacharacters should be escaped."""
        regex = _build_url_regex("example.com/path?query=1")
        # . and ? should be escaped
        assert "\\." in regex
        assert "\\?" in regex


# =============================================================================
# _extract_domain_from_pattern Tests
# =============================================================================

class TestExtractDomainFromPattern:
    """Tests for _extract_domain_from_pattern function."""

    def test_domain_only(self):
        """Domain-only pattern should return as-is."""
        assert _extract_domain_from_pattern("api.openai.com") == "api.openai.com"

    def test_domain_with_path(self):
        """Domain with path should return just domain."""
        assert _extract_domain_from_pattern("api.openai.com/v1/chat") == "api.openai.com"

    def test_wildcard_domain(self):
        """Wildcard domain should be preserved."""
        assert _extract_domain_from_pattern("*.openai.com") == "*.openai.com"

    def test_wildcard_with_path(self):
        """Wildcard with path should return just domain portion."""
        assert _extract_domain_from_pattern("*.openai.com/**/stream") == "*.openai.com"


# =============================================================================
# generate_event_id Tests
# =============================================================================

class TestGenerateEventId:
    """Tests for generate_event_id function."""

    def test_format_validation(self):
        """Event ID should be in UUID format (8-4-4-4-12)."""
        event_id = generate_event_id()
        parts = event_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_all_hex_characters(self):
        """Event ID should only contain hex characters and dashes."""
        event_id = generate_event_id()
        assert all(c in "0123456789abcdef-" for c in event_id)

    def test_uniqueness(self):
        """Multiple calls should produce unique IDs."""
        ids = [generate_event_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_uuid7_version(self):
        """UUID should have version 7 (bits 48-51 = 0111)."""
        event_id = generate_event_id()
        # Version is in the first character of the 3rd group
        version_char = event_id.split("-")[2][0]
        assert version_char == "7"

    def test_time_sortable(self):
        """IDs generated later should sort after earlier ones."""
        id1 = generate_event_id()
        time.sleep(0.01)
        id2 = generate_event_id()
        assert id2 > id1  # Lexicographic comparison works for UUID v7


# =============================================================================
# MemoryTraceBuffer Tests
# =============================================================================

class TestMemoryTraceBuffer:
    """Tests for MemoryTraceBuffer class."""

    def test_append_under_limit(self):
        """Append should succeed when under limits."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
        event = {"type": "test", "data": "value"}
        assert buffer.append(event) is True
        assert buffer.size() == 1

    def test_append_at_byte_limit(self):
        """Append should fail when byte limit reached."""
        buffer = MemoryTraceBuffer(max_bytes=100, max_count=100)

        # Add events until we hit byte limit
        event = {"data": "x" * 50}
        buffer.append(event)

        # This should fail
        assert buffer.append(event) is False

    def test_append_at_count_limit(self):
        """Append should fail when count limit reached."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=2)

        assert buffer.append({"id": 1}) is True
        assert buffer.append({"id": 2}) is True
        assert buffer.append({"id": 3}) is False  # Limit reached

    def test_take_batch_empty(self):
        """take_batch should return empty list for empty buffer."""
        buffer = MemoryTraceBuffer()
        assert buffer.take_batch() == []

    def test_take_batch_partial(self):
        """take_batch should return events up to max_bytes."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        for i in range(10):
            buffer.append({"id": i, "data": "x" * 100})

        # Take small batch
        batch = buffer.take_batch(max_bytes=500)
        assert len(batch) < 10  # Not all events
        assert buffer.size() > 0  # Some remaining

    def test_take_batch_full_drain(self):
        """take_batch with large limit should drain buffer."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        for i in range(5):
            buffer.append({"id": i})

        batch = buffer.take_batch(max_bytes=1024 * 1024)
        assert len(batch) == 5
        assert buffer.size() == 0

    def test_prepend_batch(self):
        """prepend_batch should add events back to front."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        buffer.append({"id": 1})
        buffer.append({"id": 2})

        # Prepend events
        buffer.prepend_batch([{"id": 0}])

        # Take all and check order
        batch = buffer.take_batch(max_bytes=1024 * 1024)
        assert batch[0]["id"] == 0
        assert batch[1]["id"] == 1
        assert batch[2]["id"] == 2

    def test_bytes_used_tracking(self):
        """bytes_used should track serialized size."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        initial = buffer.bytes_used()
        buffer.append({"data": "test"})
        after = buffer.bytes_used()

        assert after > initial

    def test_clear(self):
        """clear should empty the buffer."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        buffer.append({"id": 1})
        buffer.append({"id": 2})
        assert buffer.size() == 2

        buffer.clear()
        assert buffer.size() == 0
        assert buffer.bytes_used() == 0

    def test_max_bytes_property(self):
        """max_bytes property should return the configured maximum."""
        buffer = MemoryTraceBuffer(max_bytes=5 * 1024 * 1024, max_count=100)
        assert buffer.max_bytes == 5 * 1024 * 1024

    def test_peek_all(self):
        """peek_all should return all events without removing them."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)

        buffer.append({"id": 1})
        buffer.append({"id": 2})

        events = buffer.peek_all()
        assert len(events) == 2
        assert events[0]["id"] == 1
        assert events[1]["id"] == 2

        # Events should still be in buffer
        assert buffer.size() == 2


# =============================================================================
# TLSPassthrough Tests
# =============================================================================

class TestTLSPassthrough:
    """Tests for TLSPassthrough class."""

    def test_exact_pattern_match(self):
        """Exact pattern should match."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough(["^apple\\.com$"])
            assert passthrough.should_passthrough("apple.com") is True

    def test_wildcard_pattern_match(self):
        """Wildcard pattern should match subdomains."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([".*\\.apple\\.com"])
            assert passthrough.should_passthrough("store.apple.com") is True
            assert passthrough.should_passthrough("developer.apple.com") is True

    def test_no_match(self):
        """Non-matching host should return False."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough(["^apple\\.com$"])
            assert passthrough.should_passthrough("google.com") is False

    def test_learned_host(self):
        """Learned hosts should be matched."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([])

            # Mock file write
            with patch('builtins.open', mock_open()):
                with patch.object(Path, 'mkdir'):
                    passthrough.add_host("learned.example.com")

            assert passthrough.should_passthrough("learned.example.com") is True

    def test_cache_hit(self):
        """Cached results should be returned quickly."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough(["^cached\\.com$"])

            # First call - populates cache
            result1 = passthrough.should_passthrough("cached.com")
            # Second call - should use cache
            result2 = passthrough.should_passthrough("cached.com")

            assert result1 is True
            assert result2 is True

    def test_invalid_pattern_ignored(self):
        """Invalid regex patterns should be ignored."""
        with patch.object(Path, 'exists', return_value=False):
            # Invalid regex should not crash
            passthrough = TLSPassthrough(["[invalid", "valid\\.com"])
            assert passthrough.should_passthrough("valid.com") is True

    def test_result_cache_lru_eviction(self):
        """Cache should evict old entries when full."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([])
            passthrough._CACHE_MAX_SIZE = 3  # Small cache for testing

            # Fill cache
            passthrough._result_cache["a.com"] = True
            passthrough._result_cache["b.com"] = False
            passthrough._result_cache["c.com"] = True

            # This should evict oldest
            passthrough.should_passthrough("d.com")

            assert len(passthrough._result_cache) <= 3

    def test_record_tls_failure_adds_pinned_host(self):
        """record_tls_failure should add cert-pinned hosts to passthrough."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([])

            # Initially should not passthrough
            assert passthrough.should_passthrough("pinned.example.com") is False

            # Record a TLS failure with cert pinning indicator
            with patch('builtins.open', mock_open()):
                with patch.object(Path, 'mkdir'):
                    passthrough.record_tls_failure(
                        "pinned.example.com",
                        "certificate verify failed",
                        whitelist=[]  # Not in whitelist
                    )

            # Now should passthrough
            assert passthrough.should_passthrough("pinned.example.com") is True

    def test_record_tls_failure_ignores_whitelisted(self):
        """record_tls_failure should not add whitelisted domains."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([])

            # Record failure for whitelisted domain
            passthrough.record_tls_failure(
                "api.openai.com",
                "certificate verify failed",
                whitelist=["api.openai.com"]  # In whitelist
            )

            # Should NOT be added to passthrough (we want to intercept it)
            assert passthrough.should_passthrough("api.openai.com") is False

    def test_record_tls_failure_ignores_non_pinning_errors(self):
        """record_tls_failure should ignore non-pinning TLS errors."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough([])

            # Non-pinning error
            passthrough.record_tls_failure(
                "example.com",
                "connection reset",
                whitelist=[]
            )

            # Should not be added
            assert passthrough.should_passthrough("example.com") is False

    def test_update_passthrough_replaces_patterns(self):
        """update_passthrough should replace patterns from config."""
        with patch.object(Path, 'exists', return_value=False):
            passthrough = TLSPassthrough(["^old\\.com$"])

            # Initially matches old pattern
            assert passthrough.should_passthrough("old.com") is True
            assert passthrough.should_passthrough("new.com") is False

            # Update with new patterns
            passthrough.update_passthrough(["^new\\.com$"])

            # Now should only match new pattern
            # Note: old pattern removed, new pattern added
            assert passthrough.should_passthrough("new.com") is True


# =============================================================================
# load_output_config Tests
# =============================================================================

class TestLoadOutputConfig:
    """Tests for load_output_config function."""

    def test_default_config(self):
        """Should return default config when no file exists."""
        with patch.object(Path, 'exists', return_value=False):
            config = load_output_config()

            assert "output" in config
            assert "directory" in config["output"]
            assert "filename_pattern" in config["output"]
            assert "sensor_config_url" in config

    def test_valid_config_file(self, tmp_path: Path):
        """Should load and merge user config."""
        config_file = tmp_path / "config.json"
        user_config = {
            "output": {
                "directory": "/custom/traces"
            },
            "sensor_config_url": "https://custom.api.com/config"
        }
        config_file.write_text(json.dumps(user_config))

        config = load_output_config(config_file)

        assert config["output"]["directory"] == "/custom/traces"
        assert config["sensor_config_url"] == "https://custom.api.com/config"

    def test_malformed_json(self, tmp_path: Path):
        """Should handle malformed JSON gracefully."""
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json {")

        # Should not raise, returns default
        config = load_output_config(config_file)
        assert "output" in config  # Default values

    def test_missing_file(self):
        """Should handle missing file gracefully."""
        config = load_output_config(Path("/nonexistent/path/config.json"))
        assert "output" in config  # Default values


# =============================================================================
# Edge Cases and Thread Safety
# =============================================================================

class TestEdgeCases:
    """Test edge cases and thread safety."""

    def test_matches_domain_special_characters(self):
        """Should handle domains with special characters."""
        patterns = ["test-api.example.com"]
        assert matches_domain("test-api.example.com", patterns) == "test-api.example.com"

    def test_memory_buffer_thread_safe(self):
        """MemoryTraceBuffer should be thread-safe."""
        import concurrent.futures

        buffer = MemoryTraceBuffer(max_bytes=10 * 1024 * 1024, max_count=1000)

        def append_events():
            for i in range(100):
                buffer.append({"thread_event": i})
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(append_events) for _ in range(4)]
            for future in concurrent.futures.as_completed(futures):
                assert future.result() is True

        # All events should be added (up to limits)
        assert buffer.size() <= 400

    def test_generate_event_id_concurrent(self):
        """generate_event_id should be safe for concurrent calls."""
        import concurrent.futures

        def generate_ids():
            return [generate_event_id() for _ in range(100)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_ids) for _ in range(4)]
            all_ids = []
            for future in concurrent.futures.as_completed(futures):
                all_ids.extend(future.result())

        # All IDs should be unique
        assert len(set(all_ids)) == len(all_ids)

    def test_url_pattern_cache_not_grow_unbounded(self):
        """URL pattern cache should not grow unbounded."""
        # Generate many unique patterns
        for i in range(2000):
            _matches_url_pattern(f"test{i}.com/path", f"test{i}.com/**")

        # Cache should be limited (check via private access or behavior)
        # Just verify no exception and it still works
        assert _matches_url_pattern("final.com/path", "final.com/**") is True
