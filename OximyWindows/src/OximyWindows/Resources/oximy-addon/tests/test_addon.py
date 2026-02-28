"""Comprehensive unit tests for addon.py pure logic functions.

Tests cover only the pure logic functions that don't require mitmproxy context
or I/O operations. Functions with filesystem, subprocess, or network dependencies
are mocked appropriately.
"""

from __future__ import annotations

import io
import json
import os
import re

# Import the functions under test
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

from mitmproxy.addons.oximy.addon import _build_url_regex
from mitmproxy.addons.oximy.addon import _matches_url_pattern
from mitmproxy.addons.oximy.addon import _resolve_api_base_url
from mitmproxy.addons.oximy.addon import _write_force_logout_state
from mitmproxy.addons.oximy.addon import _write_proxy_state
from mitmproxy.addons.oximy.addon import contains_blacklist_word
from mitmproxy.addons.oximy.addon import DEFAULT_API_BASE_URL
from mitmproxy.addons.oximy.addon import DirectTraceUploader
from mitmproxy.addons.oximy.addon import extract_graphql_operation
from mitmproxy.addons.oximy.addon import generate_event_id
from mitmproxy.addons.oximy.addon import load_output_config
from mitmproxy.addons.oximy.addon import matches_app_origin
from mitmproxy.addons.oximy.addon import matches_domain
from mitmproxy.addons.oximy.addon import matches_host_origin
from mitmproxy.addons.oximy.addon import matches_whitelist
from mitmproxy.addons.oximy.addon import MemoryTraceBuffer
from mitmproxy.addons.oximy.addon import OXIMY_STATE_FILE
from mitmproxy.addons.oximy.addon import OximyAddon
from mitmproxy.addons.oximy.addon import TLSPassthrough

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

    def test_no_prefix_match_within_word(self):
        """Pattern should not match when URL continues with more word characters."""
        # conversation should not match conversations
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/conversation",
            "chatgpt.com/backend-api/**/conversation"
        ) is True
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/conversations",
            "chatgpt.com/backend-api/**/conversation"
        ) is False

        # me should not match messages
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/me",
            "chatgpt.com/backend-api/me"
        ) is True
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/messages",
            "chatgpt.com/backend-api/me"
        ) is False

        # completion should not match completions
        assert _matches_url_pattern(
            "claude.ai/api/organizations/org1/completion",
            "claude.ai/api/organizations/**/completion"
        ) is True
        assert _matches_url_pattern(
            "claude.ai/api/organizations/org1/completions",
            "claude.ai/api/organizations/**/completion"
        ) is False

    def test_boundary_allows_query_strings(self):
        """Pattern ending in a word should still match URLs with query strings."""
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/conversation?stream=true",
            "chatgpt.com/backend-api/**/conversation"
        ) is True

    def test_boundary_allows_subpaths(self):
        """Pattern ending in a word should still match URLs with additional path segments."""
        assert _matches_url_pattern(
            "chatgpt.com/backend-api/me/settings",
            "chatgpt.com/backend-api/me"
        ) is True


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

    def test_no_prefix_match_conversation(self):
        """conversation pattern should not match conversations endpoint."""
        patterns = ["chatgpt.com/backend-api/**/conversation"]
        assert matches_whitelist("chatgpt.com", "/backend-api/conversation", patterns) == "chatgpt.com/backend-api/**/conversation"
        assert matches_whitelist("chatgpt.com", "/backend-api/conversations", patterns) is None
        assert matches_whitelist("chatgpt.com", "/backend-api/conversations?offset=0", patterns) is None

    def test_no_prefix_match_me(self):
        """me pattern should not match messages endpoint."""
        patterns = ["chatgpt.com/backend-api/me"]
        assert matches_whitelist("chatgpt.com", "/backend-api/me", patterns) == "chatgpt.com/backend-api/me"
        assert matches_whitelist("chatgpt.com", "/backend-api/messages", patterns) is None


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

    def test_word_boundary_prevents_prefix_match(self):
        """Patterns ending with a word character should not prefix-match."""
        regex = _build_url_regex("example.com/conversation")
        pattern = re.compile(regex, re.IGNORECASE)
        assert pattern.match("example.com/conversation")
        assert pattern.match("example.com/conversation/")
        assert pattern.match("example.com/conversation?q=1")
        assert pattern.match("example.com/conversations") is None

    def test_no_boundary_for_wildcard_ending(self):
        """Patterns ending with wildcard should not add boundary."""
        regex = _build_url_regex("example.com/StreamGenerate*")
        pattern = re.compile(regex, re.IGNORECASE)
        assert pattern.match("example.com/StreamGenerateContent")
        assert pattern.match("example.com/StreamGenerate")


# =============================================================================
# generate_event_id Tests
# =============================================================================

class TestGenerateEventId:
    """Tests for generate_event_id function."""

    def test_uniqueness(self):
        """Multiple calls should produce unique IDs."""
        ids = [generate_event_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

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

    def test_api_base_url_derives_endpoints(self, tmp_path: Path):
        """api_base_url should derive sensor_config_url and ingest_api_url."""
        config_file = tmp_path / "config.json"
        user_config = {
            "api_base_url": "https://api.oximy.com/api/v1"
        }
        config_file.write_text(json.dumps(user_config))

        with patch.dict(os.environ, {}, clear=False):
            # Remove env overrides if present
            os.environ.pop("OXIMY_API_URL", None)
            os.environ.pop("OXIMY_CONFIG_URL", None)
            os.environ.pop("OXIMY_INGEST_URL", None)
            config = load_output_config(config_file)

        assert config["sensor_config_url"] == "https://api.oximy.com/api/v1/sensor-config"
        assert config.get("upload", {}).get("ingest_api_url") == "https://api.oximy.com/api/v1/ingest/network-traces"

    def test_explicit_sensor_url_overrides_api_base(self, tmp_path: Path):
        """Explicit sensor_config_url should override api_base_url derivation."""
        config_file = tmp_path / "config.json"
        user_config = {
            "api_base_url": "https://api.oximy.com/api/v1",
            "sensor_config_url": "https://custom.api.com/config"
        }
        config_file.write_text(json.dumps(user_config))

        config = load_output_config(config_file)

        # Explicit sensor_config_url takes priority
        assert config["sensor_config_url"] == "https://custom.api.com/config"


class TestResolveApiBaseUrl:
    """Tests for _resolve_api_base_url priority chain."""

    def test_default_returns_hardcoded(self):
        """Without any overrides, should return DEFAULT_API_BASE_URL."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OXIMY_API_URL", None)
            with patch("mitmproxy.addons.oximy.addon.OXIMY_DEV_CONFIG",
                       Path("/nonexistent/dev.json")):
                url = _resolve_api_base_url()
                assert url == DEFAULT_API_BASE_URL

    def test_env_var_takes_priority(self):
        """OXIMY_API_URL env var should override everything."""
        with patch.dict(os.environ, {"OXIMY_API_URL": "http://env:9999/api/v1"}):
            url = _resolve_api_base_url()
            assert url == "http://env:9999/api/v1"

    def test_env_var_strips_trailing_slash(self):
        """Trailing slash should be stripped."""
        with patch.dict(os.environ, {"OXIMY_API_URL": "http://env:9999/api/v1/"}):
            url = _resolve_api_base_url()
            assert url == "http://env:9999/api/v1"

    def test_config_base_url_used(self):
        """config_base_url argument should be used when no env var."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OXIMY_API_URL", None)
            url = _resolve_api_base_url(config_base_url="http://config:5000/api/v1")
            assert url == "http://config:5000/api/v1"

    def test_env_var_overrides_config_base(self):
        """Env var should take priority over config_base_url."""
        with patch.dict(os.environ, {"OXIMY_API_URL": "http://env:9999/api/v1"}):
            url = _resolve_api_base_url(config_base_url="http://config:5000/api/v1")
            assert url == "http://env:9999/api/v1"

    def test_dev_json_resolution(self, tmp_path: Path):
        """dev.json API_URL should be used when no env var or config base."""
        dev_json = tmp_path / "dev.json"
        dev_json.write_text(json.dumps({"API_URL": "http://dev:4000/api/v1"}))

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OXIMY_API_URL", None)
            with patch("mitmproxy.addons.oximy.addon.OXIMY_DEV_CONFIG", dev_json):
                url = _resolve_api_base_url()
                assert url == "http://dev:4000/api/v1"

    def test_config_base_overrides_dev_json(self, tmp_path: Path):
        """config_base_url should take priority over dev.json."""
        dev_json = tmp_path / "dev.json"
        dev_json.write_text(json.dumps({"API_URL": "http://dev:4000/api/v1"}))

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OXIMY_API_URL", None)
            with patch("mitmproxy.addons.oximy.addon.OXIMY_DEV_CONFIG", dev_json):
                url = _resolve_api_base_url(config_base_url="http://config:5000/api/v1")
                assert url == "http://config:5000/api/v1"


# =============================================================================
# Edge Cases and Thread Safety
# =============================================================================

class TestEdgeCases:
    """Test edge cases and thread safety."""

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


# =============================================================================
# Disk Cleanup Tests
# =============================================================================




def _make_addon_with_output_dir(tmp_path: Path) -> OximyAddon:
    """Create a minimal OximyAddon instance with _output_dir set for cleanup testing."""
    addon = object.__new__(OximyAddon)
    addon._output_dir = tmp_path
    addon._writer = None
    addon._uploader = None
    addon._last_cleanup_time = 0.0
    return addon


def _create_trace_file(directory: Path, name: str, size_bytes: int = 100, age_days: float = 0) -> Path:
    """Create a trace file with specific size and age."""
    f = directory / name
    # Write exact number of bytes
    f.write_bytes(b"x" * size_bytes)
    if age_days > 0:
        mtime = time.time() - (age_days * 86400)
        os.utime(f, (mtime, mtime))
    return f


class TestDiskCleanup:
    """Tests for _cleanup_stale_traces() method."""

    def test_cleanup_deletes_old_files(self, tmp_path: Path):
        """Files older than DISK_MAX_AGE_DAYS should be deleted."""
        addon = _make_addon_with_output_dir(tmp_path)
        old_file = _create_trace_file(tmp_path, "traces_2025-01-01.jsonl", size_bytes=100, age_days=8)
        assert old_file.exists()

        addon._cleanup_stale_traces()

        assert not old_file.exists()

    def test_cleanup_keeps_recent_files(self, tmp_path: Path):
        """Files younger than DISK_MAX_AGE_DAYS should be kept."""
        addon = _make_addon_with_output_dir(tmp_path)
        recent = _create_trace_file(tmp_path, "traces_2025-02-06.jsonl", size_bytes=100, age_days=1)

        addon._cleanup_stale_traces()

        assert recent.exists()

    def test_cleanup_enforces_size_budget(self, tmp_path: Path):
        """When total size exceeds DISK_MAX_TOTAL_BYTES, oldest files are deleted first."""
        addon = _make_addon_with_output_dir(tmp_path)
        # Create files totaling ~80 MB (over 50 MB budget), all recent
        mb = 1024 * 1024
        f1 = _create_trace_file(tmp_path, "traces_2025-02-01.jsonl", size_bytes=30 * mb, age_days=3)
        f2 = _create_trace_file(tmp_path, "traces_2025-02-02.jsonl", size_bytes=30 * mb, age_days=2)
        f3 = _create_trace_file(tmp_path, "traces_2025-02-03.jsonl", size_bytes=20 * mb, age_days=1)

        addon._cleanup_stale_traces()

        # Oldest file (f1) should be deleted to get under 50 MB
        assert not f1.exists()
        # Remaining: f2 (30 MB) + f3 (20 MB) = 50 MB, which is exactly at budget
        assert f2.exists()
        assert f3.exists()

    def test_cleanup_skips_active_file(self, tmp_path: Path):
        """The file currently being written by TraceWriter should never be deleted."""
        addon = _make_addon_with_output_dir(tmp_path)
        active_file = _create_trace_file(tmp_path, "traces_2025-01-01.jsonl", size_bytes=100, age_days=10)

        # Simulate an active writer
        mock_writer = MagicMock()
        mock_writer._current_file = active_file
        addon._writer = mock_writer

        addon._cleanup_stale_traces()

        # Active file preserved even though it's old
        assert active_file.exists()

    def test_cleanup_is_throttled(self, tmp_path: Path):
        """Cleanup should not run more than once per DISK_CLEANUP_INTERVAL."""
        addon = _make_addon_with_output_dir(tmp_path)
        old_file = _create_trace_file(tmp_path, "traces_2025-01-01.jsonl", size_bytes=100, age_days=10)

        # First run: should delete
        addon._cleanup_stale_traces()
        assert not old_file.exists()

        # Create another old file
        old_file2 = _create_trace_file(tmp_path, "traces_2024-12-01.jsonl", size_bytes=100, age_days=40)

        # Second run: should be throttled (no-op)
        addon._cleanup_stale_traces()
        assert old_file2.exists()

    def test_cleanup_handles_empty_dir(self, tmp_path: Path):
        """Empty or missing traces dir should not raise."""
        addon = _make_addon_with_output_dir(tmp_path)
        # Empty dir — should not error
        addon._cleanup_stale_traces()

        # Missing dir — should not error
        addon._output_dir = tmp_path / "nonexistent"
        addon._last_cleanup_time = 0.0
        addon._cleanup_stale_traces()

    def test_cleanup_handles_permission_error(self, tmp_path: Path):
        """Files that can't be deleted should be skipped without crashing."""
        addon = _make_addon_with_output_dir(tmp_path)
        old_file = _create_trace_file(tmp_path, "traces_2025-01-01.jsonl", size_bytes=100, age_days=10)

        # Mock unlink to raise PermissionError
        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            addon._cleanup_stale_traces()

        # Should not crash, file still exists (couldn't delete)
        assert old_file.exists()

    def test_cleanup_removes_upload_state(self, tmp_path: Path):
        """Deleted file's entry should be removed from upload state."""
        addon = _make_addon_with_output_dir(tmp_path)
        old_file = _create_trace_file(tmp_path, "traces_2025-01-01.jsonl", size_bytes=100, age_days=10)

        # Set up a mock uploader with state tracking
        mock_uploader = MagicMock()
        mock_uploader._upload_state = {str(old_file): 50}
        addon._uploader = mock_uploader

        addon._cleanup_stale_traces()

        assert not old_file.exists()
        assert str(old_file) not in mock_uploader._upload_state
        mock_uploader._save_state.assert_called()

    def test_cleanup_deletes_debug_trace_files(self, tmp_path: Path):
        """Debug trace files (all_traces_*.jsonl) should also be cleaned."""
        addon = _make_addon_with_output_dir(tmp_path)
        debug_file = _create_trace_file(tmp_path, "all_traces_2025-01-01.jsonl", size_bytes=100, age_days=10)

        addon._cleanup_stale_traces()

        assert not debug_file.exists()

    def test_cleanup_ignores_non_trace_files(self, tmp_path: Path):
        """Non-trace files in the directory should not be touched."""
        addon = _make_addon_with_output_dir(tmp_path)
        other_file = tmp_path / "config.json"
        other_file.write_text("{}")
        mtime = time.time() - (30 * 86400)
        os.utime(other_file, (mtime, mtime))

        addon._cleanup_stale_traces()

        assert other_file.exists()


# =============================================================================
# DirectTraceUploader Circuit Breaker Tests
# =============================================================================

def _make_uploader(buffer_max_bytes=1024 * 1024, buffer_max_count=100):
    """Helper: create a DirectTraceUploader with a fresh MemoryTraceBuffer."""
    buf = MemoryTraceBuffer(max_bytes=buffer_max_bytes, max_count=buffer_max_count)
    uploader = DirectTraceUploader(buf, api_url="http://test-api/ingest")
    return uploader, buf


def _mock_success_response():
    """Helper: create a mock HTTP response that returns success."""
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = b'{"success": true}'
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestDirectTraceUploaderCircuitBreaker:
    """Tests for the fail-open upload circuit breaker."""

    def test_circuit_breaker_closed_on_successful_upload(self):
        """Circuit breaker stays closed when uploads succeed."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            mock_opener.open.return_value = _mock_success_response()
            result = uploader.upload_batch()

        assert result is True
        assert uploader._circuit_breaker_failures == 0
        assert not uploader.circuit_breaker_open

    def test_circuit_breaker_opens_after_threshold_failures(self):
        """Circuit breaker opens after 3 consecutive network failures."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            mock_opener.open.side_effect = urllib.error.URLError("Connection refused")
            result = uploader.upload_batch()

        assert result is False
        assert uploader._circuit_breaker_failures >= uploader._CIRCUIT_BREAKER_THRESHOLD
        assert uploader.circuit_breaker_open

    def test_circuit_breaker_open_skips_upload_immediately(self):
        """When circuit breaker is open, upload_batch returns immediately without HTTP calls."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        # Force circuit breaker open
        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            result = uploader.upload_batch()

        assert result is False
        mock_opener.open.assert_not_called()

    def test_traces_preserved_when_circuit_breaker_open(self):
        """Traces remain in buffer (not lost) when circuit breaker blocks uploads."""
        uploader, buf = _make_uploader()
        for i in range(5):
            buf.append({"id": i})

        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener"):
            uploader.upload_batch()

        assert buf.size() == 5

    def test_circuit_breaker_half_open_allows_probe_after_cooldown(self):
        """After cooldown expires, one probe request is allowed."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        # Set circuit breaker to failed state with expired cooldown
        uploader._circuit_breaker_failures = 3
        uploader._circuit_breaker_open_until = time.time() - 1  # Cooldown already passed

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            mock_opener.open.return_value = _mock_success_response()
            result = uploader.upload_batch()

        assert result is True
        mock_opener.open.assert_called_once()
        # Circuit breaker should be reset after successful probe
        assert uploader._circuit_breaker_failures == 0
        assert not uploader.circuit_breaker_open

    def test_401_does_not_trip_circuit_breaker(self):
        """401 auth errors should not count toward circuit breaker failures."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            http_error = urllib.error.HTTPError(
                "http://test", 401, "Unauthorized", {},
                io.BytesIO(b"Unauthorized"),
            )
            mock_opener.open.side_effect = http_error
            result = uploader.upload_batch()

        assert result is False
        assert uploader._circuit_breaker_failures == 0
        assert not uploader.circuit_breaker_open

    def test_force_bypasses_circuit_breaker(self):
        """force=True (shutdown path) bypasses circuit breaker."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        # Force circuit breaker open
        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            mock_opener.open.return_value = _mock_success_response()
            result = uploader.upload_batch(force=True)

        assert result is True
        mock_opener.open.assert_called_once()

    def test_upload_all_respects_circuit_breaker(self):
        """upload_all stops immediately when circuit breaker is open."""
        uploader, buf = _make_uploader()
        for i in range(10):
            buf.append({"id": i})

        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener"):
            result = uploader.upload_all()

        assert result == 0
        assert buf.size() == 10

    def test_upload_all_force_bypasses_circuit_breaker(self):
        """upload_all(force=True) bypasses circuit breaker for shutdown flush."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            mock_opener.open.return_value = _mock_success_response()
            result = uploader.upload_all(force=True)

        assert result == 1
        assert buf.size() == 0

    @patch("mitmproxy.addons.oximy.addon._circuit_breaker_open_until", time.time() + 300)
    @patch("mitmproxy.addons.oximy.addon._circuit_breaker_failures", 3)
    def test_config_circuit_breaker_open_skips_upload(self):
        """When config fetch circuit breaker is open, uploads skip immediately."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener:
            result = uploader.upload_batch()

        assert result is False
        mock_opener.open.assert_not_called()
        assert buf.size() == 1

    def test_config_circuit_breaker_closed_upload_circuit_breaker_open_still_skips(self):
        """When config circuit breaker is closed but upload circuit breaker is open, uploads still skip."""
        uploader, buf = _make_uploader()
        buf.append({"id": 1})

        # Upload circuit breaker open, config circuit breaker closed (default state)
        uploader._circuit_breaker_open_until = time.time() + 300
        uploader._circuit_breaker_failures = 3

        with patch("mitmproxy.addons.oximy.addon._no_proxy_opener") as mock_opener, \
             patch("mitmproxy.addons.oximy.addon._circuit_breaker_open_until", 0.0), \
             patch("mitmproxy.addons.oximy.addon._circuit_breaker_failures", 0):
            result = uploader.upload_batch()

        assert result is False
        mock_opener.open.assert_not_called()


# =============================================================================
# Atomic State File Writes Tests
# =============================================================================

class TestAtomicStateFileWrites:
    """Verify that state file writes use _atomic_write to prevent corruption."""

    @patch("mitmproxy.addons.oximy.addon._atomic_write")
    def test_write_force_logout_state_uses_atomic_write(self, mock_atomic):
        _write_force_logout_state()
        mock_atomic.assert_called_once()
        call_args = mock_atomic.call_args
        assert call_args[0][0] == OXIMY_STATE_FILE
        written_json = json.loads(call_args[0][1])
        assert written_json["force_logout"] is True
        assert written_json["sensor_enabled"] is False

    @patch("mitmproxy.addons.oximy.addon._atomic_write")
    def test_write_proxy_state_uses_atomic_write(self, mock_atomic):
        with patch("mitmproxy.addons.oximy.addon.OXIMY_STATE_FILE") as mock_path:
            mock_path.exists.return_value = False
            _write_proxy_state()
        mock_atomic.assert_called_once()
        written_json = json.loads(mock_atomic.call_args[0][1])
        assert "proxy_active" in written_json

    @patch("mitmproxy.addons.oximy.addon._atomic_write")
    def test_write_proxy_state_preserves_existing_fields(self, mock_atomic):
        existing = json.dumps({"sensor_enabled": True, "tenantId": "t123"})
        with patch("mitmproxy.addons.oximy.addon.OXIMY_STATE_FILE") as mock_path:
            mock_path.exists.return_value = True
            with patch("builtins.open", mock_open(read_data=existing)):
                _write_proxy_state()
        written_json = json.loads(mock_atomic.call_args[0][1])
        assert written_json["sensor_enabled"] is True
        assert written_json["tenantId"] == "t123"
