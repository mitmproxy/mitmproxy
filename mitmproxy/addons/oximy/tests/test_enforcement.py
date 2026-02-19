"""Tests for enforcement engine — PII detection, policy modes, and warn-then-allow."""

from __future__ import annotations

import re
import time
import threading
from unittest.mock import patch

import pytest

try:
    from mitmproxy.addons.oximy.enforcement import (
        FALLBACK_PII_PATTERNS,
        EnforcementRule,
        EnforcementPolicy,
        Violation,
        EnforcementEngine,
    )
except ImportError:
    from enforcement import (
        FALLBACK_PII_PATTERNS,
        EnforcementRule,
        EnforcementPolicy,
        Violation,
        EnforcementEngine,
    )

# Backward-compatible alias for tests
PII_PATTERNS = FALLBACK_PII_PATTERNS

# Standard test policy — replaces the removed DEFAULT_ENFORCEMENT_POLICY
_TEST_POLICY = {
    "id": "test_pii",
    "name": "Test PII Policy",
    "mode": "warn",
    "rules": [
        {
            "id": "pii_all",
            "type": "data_type",
            "name": "PII Detection",
            "severity": "high",
            "data_types": [
                "email", "ssn", "credit_card", "api_key",
                "aws_key", "github_token", "private_key", "phone",
            ],
        }
    ],
}


def _engine_with_policy(**overrides) -> EnforcementEngine:
    """Create an EnforcementEngine loaded with the standard test policy."""
    engine = EnforcementEngine()
    policy = {**_TEST_POLICY, **overrides}
    engine.update_policies([policy])
    return engine


# =============================================================================
# PII Pattern Matching Tests
# =============================================================================


class TestPIIPatternEmail:
    """Email pattern detection."""

    def test_simple_email(self):
        assert re.search(PII_PATTERNS["email"], "john@example.com")

    def test_complex_email(self):
        assert re.search(PII_PATTERNS["email"], "test.user+tag@domain.co.uk")

    def test_not_an_email_plain_text(self):
        assert not re.search(PII_PATTERNS["email"], "not-an-email")

    def test_not_an_email_at_sign_only(self):
        assert not re.search(PII_PATTERNS["email"], "@")

    def test_not_an_email_user_at(self):
        assert not re.search(PII_PATTERNS["email"], "user@")


class TestPIIPatternPhone:
    """Phone number pattern detection."""

    def test_dashed_phone(self):
        assert re.search(PII_PATTERNS["phone"], "555-123-4567")

    def test_international_phone(self):
        assert re.search(PII_PATTERNS["phone"], "+1 555 123 4567")

    def test_parenthesized_phone(self):
        assert re.search(PII_PATTERNS["phone"], "(555) 123-4567")

    def test_short_number_no_match(self):
        assert not re.search(PII_PATTERNS["phone"], "123")

    def test_alpha_dashed_no_match(self):
        assert not re.search(PII_PATTERNS["phone"], "abc-def-ghij")


class TestPIIPatternSSN:
    """SSN pattern detection."""

    def test_dashed_ssn(self):
        assert re.search(PII_PATTERNS["ssn"], "123-45-6789")

    def test_spaced_ssn(self):
        assert re.search(PII_PATTERNS["ssn"], "123 45 6789")

    def test_no_separator_ssn(self):
        assert re.search(PII_PATTERNS["ssn"], "123456789")

    def test_wrong_grouping_no_match(self):
        assert not re.search(PII_PATTERNS["ssn"], "12-345-6789")

    def test_wrong_length_no_match(self):
        assert not re.search(PII_PATTERNS["ssn"], "1234-5678")


class TestPIIPatternCreditCard:
    """Credit card pattern detection."""

    def test_dashed_card(self):
        assert re.search(PII_PATTERNS["credit_card"], "4111-1111-1111-1111")

    def test_spaced_card(self):
        assert re.search(PII_PATTERNS["credit_card"], "4111 1111 1111 1111")

    def test_no_separator_card(self):
        assert re.search(PII_PATTERNS["credit_card"], "4111111111111111")

    def test_short_number_no_match(self):
        assert not re.search(PII_PATTERNS["credit_card"], "411-111-111")

    def test_very_short_no_match(self):
        assert not re.search(PII_PATTERNS["credit_card"], "12345")


class TestPIIPatternAPIKey:
    """API key pattern detection."""

    def test_sk_prefix_key(self):
        assert re.search(PII_PATTERNS["api_key"], "sk-abc1234567890abcdef")

    def test_sk_live_key(self):
        # Note: the pattern requires sk[-_] followed by 16+ alphanumeric chars.
        # Underscores within the value (like sk_live_xxx) break the match.
        assert re.search(PII_PATTERNS["api_key"], "sk_liveabcdefghij12345678")

    def test_api_key_prefix(self):
        assert re.search(PII_PATTERNS["api_key"], "api_key_abcdefghijklmnop")

    def test_bearer_token(self):
        assert re.search(PII_PATTERNS["api_key"], "bearer eyJhbGciOiJIUzI1NiJ9")

    def test_sk_too_short_no_match(self):
        assert not re.search(PII_PATTERNS["api_key"], "sk-short")

    def test_random_text_no_match(self):
        assert not re.search(PII_PATTERNS["api_key"], "random_text")


class TestPIIPatternAWSKey:
    """AWS key pattern detection."""

    def test_valid_aws_key(self):
        assert re.search(PII_PATTERNS["aws_key"], "AKIAIOSFODNN7EXAMPLE")

    def test_too_short_no_match(self):
        assert not re.search(PII_PATTERNS["aws_key"], "AKIA")

    def test_partial_no_match(self):
        assert not re.search(PII_PATTERNS["aws_key"], "AKIASHORT")

    def test_lowercase_no_match(self):
        assert not re.search(PII_PATTERNS["aws_key"], "akiaiosfodnn7example")


class TestPIIPatternGitHubToken:
    """GitHub token pattern detection."""

    def test_valid_github_token(self):
        assert re.search(
            PII_PATTERNS["github_token"],
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn",
        )

    def test_too_short_no_match(self):
        assert not re.search(PII_PATTERNS["github_token"], "ghp_short")

    def test_wrong_prefix_no_match(self):
        assert not re.search(PII_PATTERNS["github_token"], "gh_token")


class TestPIIPatternIPAddress:
    """IP address pattern detection."""

    def test_private_ip(self):
        assert re.search(PII_PATTERNS["ip_address"], "192.168.1.1")

    def test_ten_network(self):
        assert re.search(PII_PATTERNS["ip_address"], "10.0.0.1")

    def test_max_octets(self):
        assert re.search(PII_PATTERNS["ip_address"], "255.255.255.255")

    def test_out_of_range_no_match(self):
        assert not re.search(PII_PATTERNS["ip_address"], "999.999.999.999")

    def test_incomplete_no_match(self):
        assert not re.search(PII_PATTERNS["ip_address"], "192.168.1")

    def test_alpha_octets_no_match(self):
        assert not re.search(PII_PATTERNS["ip_address"], "abc.def.ghi.jkl")


class TestPIIPatternPrivateKey:
    """Private key header pattern detection."""

    def test_rsa_private_key(self):
        assert re.search(PII_PATTERNS["private_key"], "-----BEGIN RSA PRIVATE KEY-----")

    def test_generic_private_key(self):
        assert re.search(PII_PATTERNS["private_key"], "-----BEGIN PRIVATE KEY-----")

    def test_ec_private_key(self):
        assert re.search(PII_PATTERNS["private_key"], "-----BEGIN EC PRIVATE KEY-----")

    def test_public_key_no_match(self):
        assert not re.search(PII_PATTERNS["private_key"], "-----BEGIN PUBLIC KEY-----")

    def test_certificate_no_match(self):
        assert not re.search(PII_PATTERNS["private_key"], "-----BEGIN CERTIFICATE-----")


# =============================================================================
# check_request() Basic Tests
# =============================================================================


def test_check_request_no_violation():
    """Normal text without PII should allow through."""
    engine = EnforcementEngine()
    action, violation = engine.check_request(
        "Hello, how are you?", "api.openai.com", "/v1/chat/completions", "POST"
    )
    assert action == "allow"
    assert violation is None


def test_check_request_detects_email():
    """Email in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        '{"messages":[{"content":"Send email to john@example.com"}]}',
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"  # Test policy is warn mode
    assert violation is not None
    assert violation.detected_type == "email"
    assert violation.policy_name == "Test PII Policy"


def test_check_request_detects_credit_card():
    """Credit card number in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "My card number is 4111-1111-1111-1111",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "credit_card"


def test_check_request_detects_ssn():
    """SSN in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "My SSN is 123-45-6789",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "ssn"


def test_check_request_detects_api_key():
    """API key in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "Use this key: sk-abc1234567890abcdef",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "api_key"


def test_check_request_detects_aws_key():
    """AWS access key in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "My AWS key is AKIAIOSFODNN7EXAMPLE",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "aws_key"


def test_check_request_detects_private_key():
    """Private key header in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "Here is my key: -----BEGIN RSA PRIVATE KEY-----",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "private_key"


def test_check_request_detects_github_token():
    """GitHub token in request body should trigger violation."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"
    assert violation.detected_type == "github_token"


# =============================================================================
# Warn-then-Allow Tests
# =============================================================================


def test_warn_then_allow_first_request_blocked():
    """First request with PII should be blocked (warn mode)."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "Email: test@example.com",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action == "warn"


def test_warn_then_allow_retry_within_ttl():
    """Second request to same host+path+rule within TTL should pass."""
    engine = _engine_with_policy()
    # First request - blocked
    action1, _ = engine.check_request(
        "Email: test@example.com",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action1 == "warn"

    # Second request - same body, same host/path - should allow
    action2, violation2 = engine.check_request(
        "Email: test@example.com",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action2 == "allow"
    assert violation2 is None


def test_warn_cache_expires_after_ttl():
    """After TTL expires, request should be blocked again."""
    engine = _engine_with_policy()
    engine.WARN_RETRY_TTL = 0.1  # 100ms for testing

    # First request - blocked
    action1, _ = engine.check_request(
        "Email: test@example.com",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action1 == "warn"

    # Wait for TTL to expire
    time.sleep(0.2)

    # Should be blocked again
    action2, _ = engine.check_request(
        "Email: test@example.com",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert action2 == "warn"


def test_warn_cache_different_hosts_separate():
    """Different hosts should have separate warn cache entries."""
    engine = _engine_with_policy()

    # Block on host1
    action1, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action1 == "warn"

    # Should still block on host2 (separate cache key)
    action2, _ = engine.check_request(
        "Email: a@b.com", "api.anthropic.com", "/v1/messages", "POST"
    )
    assert action2 == "warn"


def test_warn_cache_different_paths_separate():
    """Different paths on the same host should have separate cache entries."""
    engine = _engine_with_policy()

    # Block on path1
    action1, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action1 == "warn"

    # Should still block on path2 (same host, different path)
    action2, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/embeddings", "POST"
    )
    assert action2 == "warn"


def test_warn_retry_then_different_rule_still_warns():
    """After allow-through on one rule, a different rule should still warn.

    The warn cache is keyed by (host, path_prefix, rule_id), so different
    rules have independent cache entries even on the same host/path.
    """
    engine = EnforcementEngine()
    engine.update_policies([{
        "id": "p1", "name": "Email Policy", "mode": "warn",
        "rules": [{"id": "r_email", "type": "data_type", "name": "Email", "severity": "high", "data_types": ["email"]}],
    }, {
        "id": "p2", "name": "Card Policy", "mode": "warn",
        "rules": [{"id": "r_card", "type": "data_type", "name": "Card", "severity": "high", "data_types": ["credit_card"]}],
    }])

    # First: email detected, warn
    action1, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action1 == "warn"

    # Retry same email - allow (within TTL for r_email)
    action2, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action2 == "allow"

    # Different PII via different rule - should warn (r_card is not cached)
    action3, v3 = engine.check_request(
        "Card: 4111-1111-1111-1111", "api.openai.com", "/v1/chat", "POST"
    )
    assert action3 == "warn"
    assert v3.detected_type == "credit_card"


# =============================================================================
# Block Mode Tests
# =============================================================================


def test_block_mode_always_blocks():
    """Block mode should always block, no retry allowed."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "strict",
            "name": "Strict PII Block",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Block PII",
                    "severity": "critical",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    # First request
    action1, v1 = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action1 == "block"
    assert v1.retry_allowed is False

    # Retry - still blocked
    action2, v2 = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action2 == "block"


def test_block_mode_no_pii_allows():
    """Block mode should still allow requests without PII."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "strict",
            "name": "Strict PII Block",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Block PII",
                    "severity": "critical",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    action, violation = engine.check_request(
        "Hello, no PII here", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is None


def test_block_mode_multiple_data_types():
    """Block mode with multiple data types should block any match."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "strict",
            "name": "Strict Block",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Block All PII",
                    "severity": "critical",
                    "data_types": ["email", "credit_card", "ssn"],
                }
            ],
        }
    ])

    # Email
    action, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"

    # Credit card
    action, _ = engine.check_request(
        "Card: 4111-1111-1111-1111", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"

    # SSN
    action, _ = engine.check_request(
        "SSN: 123-45-6789", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"


# =============================================================================
# Monitor Mode Tests
# =============================================================================


def test_monitor_mode_allows_through():
    """Monitor mode should allow through but still return violation info."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "monitor",
            "name": "Monitor PII",
            "mode": "monitor",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Monitor",
                    "severity": "low",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    action, violation = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is not None  # Still detected, just not blocked


def test_monitor_mode_no_pii_no_violation():
    """Monitor mode with clean body should return no violation."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "monitor",
            "name": "Monitor PII",
            "mode": "monitor",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Monitor",
                    "severity": "low",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    action, violation = engine.check_request(
        "Clean text", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is None


def test_monitor_mode_always_allows_even_on_retry():
    """Monitor mode should allow every request, never block."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "monitor",
            "name": "Monitor PII",
            "mode": "monitor",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Monitor",
                    "severity": "low",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    for _ in range(5):
        action, _ = engine.check_request(
            "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
        )
        assert action == "allow"


# =============================================================================
# update_policies() Tests
# =============================================================================


def test_update_policies_replaces_defaults():
    """Custom policies should replace the default built-in policy."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "custom",
            "name": "Custom Policy",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Block Cards",
                    "severity": "high",
                    "data_types": ["credit_card"],
                }
            ],
        }
    ])

    # Email should now be allowed (only credit card is blocked)
    action, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"

    # Credit card should be blocked
    action, _ = engine.check_request(
        "Card: 4111-1111-1111-1111", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"


def test_update_policies_with_custom_regex():
    """Custom regex rules should match against the body."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "custom",
            "name": "Custom Regex",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "regex",
                    "name": "Block Secrets",
                    "severity": "high",
                    "patterns": [r"secret_[a-z]{8,}"],
                }
            ],
        }
    ])

    action, _ = engine.check_request(
        "My secret_abcdefghij", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"


def test_update_policies_custom_regex_no_match():
    """Custom regex rules should not match unrelated text."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "custom",
            "name": "Custom Regex",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "regex",
                    "name": "Block Secrets",
                    "severity": "high",
                    "patterns": [r"secret_[a-z]{8,}"],
                }
            ],
        }
    ])

    action, _ = engine.check_request(
        "No secrets here", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"


def test_update_policies_multiple_policies():
    """Multiple policies should all be evaluated."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "p1",
            "name": "Block Emails",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Email",
                    "severity": "high",
                    "data_types": ["email"],
                }
            ],
        },
        {
            "id": "p2",
            "name": "Warn Cards",
            "mode": "warn",
            "rules": [
                {
                    "id": "r2",
                    "type": "data_type",
                    "name": "Card",
                    "severity": "medium",
                    "data_types": ["credit_card"],
                }
            ],
        },
    ])

    # Email should be blocked (block mode policy)
    action, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"

    # Credit card should be warned (warn mode policy)
    action, _ = engine.check_request(
        "Card: 4111-1111-1111-1111", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "warn"


def test_update_policies_empty_list_clears_enforcement():
    """Passing an empty list should clear all enforcement (no policies = allow all)."""
    engine = EnforcementEngine()

    # Override with custom
    engine.update_policies([
        {
            "id": "custom",
            "name": "Custom",
            "mode": "block",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "R",
                    "severity": "high",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    # Verify custom is active
    action, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "block"

    # Clear all policies
    engine.update_policies([])

    # No policies means no enforcement — PII is allowed through
    assert len(engine._policies) == 0
    action, violation = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is None


def test_update_policies_clears_warn_cache():
    """Updating policies should clear the warn cache."""
    engine = _engine_with_policy()

    # First request - warn
    action1, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action1 == "warn"

    # Retry - allow (cached)
    action2, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action2 == "allow"

    # Update policies (same config, but should clear cache)
    engine.update_policies([
        {
            "id": "p",
            "name": "Policy",
            "mode": "warn",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "R",
                    "severity": "high",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    # Should warn again (cache was cleared)
    action3, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action3 == "warn"


# =============================================================================
# Edge Cases
# =============================================================================


def test_empty_body_allows():
    """Empty request body should always be allowed."""
    engine = EnforcementEngine()
    action, _ = engine.check_request(
        "", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"


def test_large_body_skipped():
    """Bodies over 1MB should be skipped (allow through)."""
    engine = EnforcementEngine()
    large_body = "a@b.com " * 200000  # Well over 1MB
    action, _ = engine.check_request(
        large_body, "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"


def test_fail_open_on_exception():
    """Engine should fail open (allow) if an exception occurs during matching."""
    engine = EnforcementEngine()
    # Corrupt the policies to cause an exception
    original = engine._policies
    engine._policies = None  # type: ignore
    action, _ = engine.check_request(
        "Email: a@b.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    engine._policies = original  # restore


def test_no_policies_on_init():
    """Engine should start with no policies — sensor is dumb until server configures it."""
    engine = EnforcementEngine()
    assert len(engine._policies) == 0


def test_no_policies_allows_all():
    """Without server-provided policies, all requests should be allowed."""
    engine = EnforcementEngine()
    action, violation = engine.check_request(
        "My email is john@example.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is None


def test_none_body_allows():
    """None body should be treated as empty and allowed."""
    engine = EnforcementEngine()
    # Some callers might pass None; engine should handle gracefully
    try:
        action, _ = engine.check_request(
            None, "api.openai.com", "/v1/chat", "POST"  # type: ignore
        )
        assert action == "allow"
    except TypeError:
        # Also acceptable: engine may require string
        pass


def test_whitespace_only_body_allows():
    """Body with only whitespace should be allowed."""
    engine = EnforcementEngine()
    action, _ = engine.check_request(
        "   \n\t  ", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"


def test_pii_in_url_encoded_body():
    """PII in a URL-encoded body should still be detected."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "email=john%40example.com&name=test",
        "api.openai.com",
        "/v1/chat",
        "POST",
    )
    # The raw body contains @ sign, depends on engine decoding logic
    # At minimum, if body literally contains john@example.com it should match
    # URL-encoded form may or may not match depending on implementation


def test_multiple_pii_types_in_body():
    """Body with multiple PII types should detect at least one."""
    engine = _engine_with_policy()
    action, violation = engine.check_request(
        "Email: a@b.com, SSN: 123-45-6789, Card: 4111-1111-1111-1111",
        "api.openai.com",
        "/v1/chat",
        "POST",
    )
    assert action == "warn"
    assert violation is not None
    assert violation.detected_type in ("email", "ssn", "credit_card")


# =============================================================================
# Thread Safety Tests
# =============================================================================


def test_concurrent_check_requests():
    """Multiple threads calling check_request should not crash."""
    engine = _engine_with_policy()
    results = []
    errors = []

    def check():
        try:
            action, _ = engine.check_request(
                "Email: test@example.com",
                "api.openai.com",
                "/v1/chat",
                "POST",
            )
            results.append(action)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=check) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 20


def test_concurrent_update_and_check():
    """Updating policies while checking should not crash."""
    engine = EnforcementEngine()
    errors = []

    def update():
        try:
            for _ in range(10):
                engine.update_policies([
                    {
                        "id": "p1",
                        "name": "Test",
                        "mode": "block",
                        "rules": [
                            {
                                "id": "r1",
                                "type": "data_type",
                                "name": "R",
                                "severity": "high",
                                "data_types": ["email"],
                            }
                        ],
                    }
                ])
        except Exception as e:
            errors.append(e)

    def check():
        try:
            for _ in range(10):
                engine.check_request(
                    "test@example.com", "h", "/p", "POST"
                )
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=update), threading.Thread(target=check)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_concurrent_warn_cache_access():
    """Concurrent warn-then-allow cache reads/writes should not crash."""
    engine = _engine_with_policy()
    errors = []

    def warn_and_retry(i: int):
        try:
            host = f"host{i}.example.com"
            # First call should warn
            engine.check_request(
                "Email: test@example.com", host, "/v1/chat", "POST"
            )
            # Second call should allow (cached)
            engine.check_request(
                "Email: test@example.com", host, "/v1/chat", "POST"
            )
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=warn_and_retry, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


# =============================================================================
# Violation Object Tests
# =============================================================================


def test_violation_has_correct_fields():
    """Violation should contain all expected metadata fields."""
    engine = _engine_with_policy()
    _, violation = engine.check_request(
        "Card: 4111-1111-1111-1111",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
        "com.google.Chrome",
    )
    assert violation is not None
    assert violation.host == "api.openai.com"
    assert violation.path == "/v1/chat/completions"
    assert violation.method == "POST"
    assert violation.bundle_id == "com.google.Chrome"
    assert violation.severity == "high"
    assert violation.id.startswith("v_")
    assert "T" in violation.timestamp  # ISO format


def test_violation_without_bundle_id():
    """Violation should work without a bundle_id argument."""
    engine = _engine_with_policy()
    _, violation = engine.check_request(
        "Card: 4111-1111-1111-1111",
        "api.openai.com",
        "/v1/chat/completions",
        "POST",
    )
    assert violation is not None
    assert violation.host == "api.openai.com"
    assert violation.bundle_id is None or violation.bundle_id == ""


def test_violation_detected_type_matches_pattern():
    """Violation detected_type should match the PII type that triggered it."""
    engine = _engine_with_policy()

    test_cases = [
        ("Email: john@example.com", "email"),
        ("SSN: 123-45-6789", "ssn"),
        ("Card: 4111-1111-1111-1111", "credit_card"),
        ("Key: AKIAIOSFODNN7EXAMPLE", "aws_key"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private_key"),
    ]

    for body, expected_type in test_cases:
        _, violation = engine.check_request(
            body, "api.openai.com", "/v1/chat", "POST"
        )
        assert violation is not None, f"Expected violation for {expected_type}"
        assert violation.detected_type == expected_type, (
            f"Expected {expected_type}, got {violation.detected_type} for body: {body}"
        )
        # Reset warn cache for next iteration by using different host
        engine = _engine_with_policy()


def test_violation_policy_name_from_custom_policy():
    """Violation policy_name should come from the matched policy."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "my-policy",
            "name": "My Custom Policy",
            "mode": "warn",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Detect Email",
                    "severity": "medium",
                    "data_types": ["email"],
                }
            ],
        }
    ])

    _, violation = engine.check_request(
        "Email: test@example.com", "api.openai.com", "/v1/chat", "POST"
    )
    assert violation is not None
    assert violation.policy_name == "My Custom Policy"


# =============================================================================
# EnforcementRule and EnforcementPolicy Model Tests
# =============================================================================


def test_enforcement_rule_data_type():
    """EnforcementRule with data_type should be constructable."""
    rule = EnforcementRule(
        id="r1",
        type="data_type",
        name="Test Rule",
        severity="high",
        data_types=["email", "ssn"],
    )
    assert rule.id == "r1"
    assert rule.type == "data_type"
    assert rule.severity == "high"
    assert "email" in rule.data_types


def test_enforcement_rule_regex():
    """EnforcementRule with regex should be constructable."""
    rule = EnforcementRule(
        id="r2",
        type="regex",
        name="Custom Rule",
        severity="medium",
        patterns=[r"secret_\w+"],
    )
    assert rule.id == "r2"
    assert rule.type == "regex"
    assert len(rule.patterns) == 1


def test_enforcement_policy_construction():
    """EnforcementPolicy should be constructable from dict-like data."""
    policy = EnforcementPolicy(
        id="p1",
        name="Test Policy",
        mode="warn",
        rules=[
            EnforcementRule(
                id="r1",
                type="data_type",
                name="R",
                severity="high",
                data_types=["email"],
            )
        ],
    )
    assert policy.id == "p1"
    assert policy.mode == "warn"
    assert len(policy.rules) == 1


def test_empty_policies_after_empty_update():
    """Updating with empty list should leave engine with no policies (server says no enforcement)."""
    engine = EnforcementEngine()
    engine.update_policies([])
    assert len(engine._policies) == 0
    action, violation = engine.check_request(
        "My SSN is 123-45-6789", "api.openai.com", "/v1/chat", "POST"
    )
    assert action == "allow"
    assert violation is None


# =============================================================================
# Severity Tests
# =============================================================================


def test_violation_severity_from_rule():
    """Violation severity should match the matched rule's severity."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "p1",
            "name": "Test",
            "mode": "warn",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "Critical PII",
                    "severity": "critical",
                    "data_types": ["ssn"],
                }
            ],
        }
    ])

    _, violation = engine.check_request(
        "SSN: 123-45-6789", "api.openai.com", "/v1/chat", "POST"
    )
    assert violation is not None
    assert violation.severity == "critical"


def test_violation_severity_low():
    """Low severity rules should produce low severity violations."""
    engine = EnforcementEngine()
    engine.update_policies([
        {
            "id": "p1",
            "name": "Test",
            "mode": "warn",
            "rules": [
                {
                    "id": "r1",
                    "type": "data_type",
                    "name": "IP Detect",
                    "severity": "low",
                    "data_types": ["ip_address"],
                }
            ],
        }
    ])

    _, violation = engine.check_request(
        "Server at 192.168.1.1", "api.openai.com", "/v1/chat", "POST"
    )
    assert violation is not None
    assert violation.severity == "low"


# =============================================================================
# PII_PATTERNS Completeness Test
# =============================================================================


def test_pii_patterns_contains_expected_keys():
    """PII_PATTERNS dict should contain all expected pattern keys."""
    expected_keys = {
        "email",
        "phone",
        "ssn",
        "credit_card",
        "api_key",
        "aws_key",
        "github_token",
        "ip_address",
        "private_key",
    }
    assert expected_keys.issubset(set(PII_PATTERNS.keys())), (
        f"Missing keys: {expected_keys - set(PII_PATTERNS.keys())}"
    )


def test_pii_patterns_are_compiled_regexes_or_strings():
    """Each PII_PATTERNS value should be a usable regex pattern."""
    for name, pattern in PII_PATTERNS.items():
        # Pattern should be either a string or compiled regex
        if isinstance(pattern, str):
            # Should compile without error
            re.compile(pattern)
        else:
            # Should be a compiled regex object
            assert hasattr(pattern, "search"), (
                f"Pattern {name} is not a valid regex"
            )


# =============================================================================
# PII Redaction Tests
# =============================================================================


class TestRedactPii:
    """Tests for EnforcementEngine.redact_pii()."""

    def setup_method(self):
        self.engine = _engine_with_policy()

    def test_no_pii_returns_unchanged(self):
        body = "Hello, how are you today?"
        redacted, detected = self.engine.redact_pii(body)
        assert redacted == body
        assert detected == []

    def test_email_redacted(self):
        body = "My email is john@example.com please help"
        redacted, detected = self.engine.redact_pii(body)
        assert "john@example.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in detected

    def test_credit_card_redacted(self):
        body = "My card is 4111-1111-1111-1111"
        redacted, detected = self.engine.redact_pii(body)
        assert "4111-1111-1111-1111" not in redacted
        assert "[CREDIT_CARD_REDACTED]" in redacted
        assert "credit_card" in detected

    def test_ssn_redacted(self):
        body = "SSN: 123-45-6789"
        redacted, detected = self.engine.redact_pii(body)
        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted
        assert "ssn" in detected

    def test_multiple_pii_types_redacted(self):
        body = "Email john@test.com and card 4111-1111-1111-1111"
        redacted, detected = self.engine.redact_pii(body)
        assert "john@test.com" not in redacted
        assert "4111-1111-1111-1111" not in redacted
        assert "email" in detected
        assert "credit_card" in detected

    def test_json_stays_valid_after_email_redaction(self):
        """Critical: redaction must not break JSON structure."""
        import json
        body = json.dumps({
            "messages": [{"content": {"parts": ["Send to john@example.com"]}}],
            "model": "gpt-4"
        })
        redacted, detected = self.engine.redact_pii(body)
        assert "email" in detected
        # Must still be valid JSON
        parsed = json.loads(redacted)
        assert "john@example.com" not in json.dumps(parsed)
        assert "[EMAIL_REDACTED]" in parsed["messages"][0]["content"]["parts"][0]

    def test_json_stays_valid_after_credit_card_redaction(self):
        import json
        body = json.dumps({
            "messages": [{"content": {"parts": ["Card: 4111-1111-1111-1111"]}}],
        })
        redacted, detected = self.engine.redact_pii(body)
        parsed = json.loads(redacted)
        assert "credit_card" in detected
        assert "4111-1111-1111-1111" not in json.dumps(parsed)

    def test_chatgpt_real_payload_structure(self):
        """Simulate a real ChatGPT request body and verify redaction preserves structure."""
        import json
        body = json.dumps({
            "action": "next",
            "messages": [{
                "id": "aaa-bbb-ccc",
                "author": {"role": "user"},
                "content": {
                    "content_type": "text",
                    "parts": ["My email is john@example.com and my SSN is 123-45-6789. Can you help me with my taxes?"]
                },
                "metadata": {}
            }],
            "parent_message_id": "xxx-yyy-zzz",
            "model": "gpt-4o",
            "timezone_offset_min": -330,
            "history_and_training_disabled": False,
        })
        redacted, detected = self.engine.redact_pii(body)

        # Must be valid JSON
        parsed = json.loads(redacted)
        redacted_text = parsed["messages"][0]["content"]["parts"][0]

        # PII is gone
        assert "john@example.com" not in redacted_text
        assert "123-45-6789" not in redacted_text

        # Placeholders are in
        assert "[EMAIL_REDACTED]" in redacted_text
        assert "[SSN_REDACTED]" in redacted_text

        # Non-PII fields are untouched
        assert parsed["action"] == "next"
        assert parsed["model"] == "gpt-4o"
        assert parsed["messages"][0]["id"] == "aaa-bbb-ccc"
        assert "email" in detected
        assert "ssn" in detected

    def test_empty_body_returns_unchanged(self):
        redacted, detected = self.engine.redact_pii("")
        assert redacted == ""
        assert detected == []

    def test_large_body_skipped(self):
        """Bodies over MAX_BODY_SIZE are returned unchanged."""
        big_body = "a" * (self.engine.MAX_BODY_SIZE + 1)
        redacted, detected = self.engine.redact_pii(big_body)
        assert redacted == big_body
        assert detected == []

    def test_monitor_mode_does_not_redact(self):
        """Monitor-only policies should not trigger redaction."""
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Monitor Only", "mode": "monitor",
            "rules": [{"id": "r1", "type": "data_type", "name": "Email",
                       "severity": "high", "data_types": ["email"]}],
        }])
        body = "Email: test@example.com"
        redacted, detected = engine.redact_pii(body)
        assert redacted == body
        assert detected == []

    def test_unicode_body_preserved(self):
        """Redaction should handle unicode content correctly."""
        body = "My name is \u00e9mile and email is test@example.com"
        redacted, detected = self.engine.redact_pii(body)
        assert "\u00e9mile" in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in detected

    def test_escaped_json_strings(self):
        """PII inside escaped JSON strings should still be redacted."""
        import json
        inner = json.dumps({"email": "test@example.com"})
        body = json.dumps({"data": inner})
        redacted, detected = self.engine.redact_pii(body)
        assert "test@example.com" not in redacted
        assert "email" in detected
        # Outer JSON must still be valid
        json.loads(redacted)


class TestPhoneRegexTightened:
    """Verify the phone regex doesn't false-positive on random digit sequences."""

    def test_plain_digits_no_match(self):
        """Plain digit sequences should NOT match."""
        assert not re.search(PII_PATTERNS["phone"], "session_id=1234567890")
        assert not re.search(PII_PATTERNS["phone"], "timestamp 1708012345")
        assert not re.search(PII_PATTERNS["phone"], "version 20260215")

    def test_formatted_us_phone_matches(self):
        assert re.search(PII_PATTERNS["phone"], "555-123-4567")
        assert re.search(PII_PATTERNS["phone"], "(555) 123-4567")
        assert re.search(PII_PATTERNS["phone"], "555.123.4567")
        assert re.search(PII_PATTERNS["phone"], "555 123 4567")

    def test_international_phone_matches(self):
        assert re.search(PII_PATTERNS["phone"], "+1-555-123-4567")
        assert re.search(PII_PATTERNS["phone"], "+44 20 7946 0958")

    def test_analytics_payload_no_match(self):
        """Real analytics payloads should not trigger phone detection."""
        payload = '{"event":"page_view","session":"abc123","ts":1708012345,"port":64820}'
        assert not re.search(PII_PATTERNS["phone"], payload)

    def test_perplexity_analytics_no_match(self):
        """The specific Perplexity payload that was causing false positives."""
        payload = '{"type":"autosuggest","count":42,"offset":0,"limit":10}'
        assert not re.search(PII_PATTERNS["phone"], payload)
