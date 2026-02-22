"""End-to-end enforcement tests: simulate real AI service payloads through
normalize → check_request → redact_pii pipeline.

Tests cover every whitelisted AI service and every encoding path:
- ChatGPT JSON payloads + SSE streaming
- Gemini protobuf (decoded JSON), anti-hijack prefixed, REST JSON API
- DeepSeek JSON + SSE streaming
- Perplexity SSE streaming
- Grok JSON
- Microsoft Copilot JSON
- HuggingFace Chat JSON
- OpenRouter JSON
- Replit GraphQL + MessagePack WebSocket
- Canva AI JSON
- Raycast JSON
- Conductor GraphQL JSON
- Granola SSE + JSON
- Encoding paths: gzip, URL-encoded, base64, msgpack, anti-hijack variants

These tests DO NOT require a browser — they simulate the exact data shapes
that the addon processes internally.
"""

from __future__ import annotations

import base64
import gzip
import json
import urllib.parse

try:
    from mitmproxy.addons.oximy.enforcement import EnforcementEngine
    from mitmproxy.addons.oximy.normalize import normalize_body
except ImportError:
    from enforcement import EnforcementEngine
    from normalize import normalize_body


# ---------------------------------------------------------------------------
# Realistic policies matching the real sensor-config
# ---------------------------------------------------------------------------

REAL_PII_POLICY = {
    "id": "6997968afb55bdf4664f32be",
    "name": "PII Protection Policy",
    "mode": "block",
    "rules": [
        {
            "id": "0e5cd619-13f2-4874-a0e8-2507c8808e35",
            "type": "data_type",
            "name": "Data Type Detection",
            "severity": "high",
            "dataTypes": [
                "email", "phone", "ssn", "credit_card",
                "api_key", "github_token", "ip_address",
                "aws_key", "private_key",
            ],
        }
    ],
}

SECRETS_POLICY = {
    "id": "69979fdbfb55bdf4665049dc",
    "name": "Secrets & Credentials Policy",
    "mode": "block",
    "rules": [
        {
            "id": "624ef2b5-3726-4db0-9438-9c4b9a45bbfa",
            "type": "data_type",
            "name": "Data Type Detection",
            "severity": "high",
            "dataTypes": [
                "api_key", "aws_key", "github_token", "private_key",
                "credit_card", "email", "ssn", "phone", "ip_address",
            ],
        }
    ],
}


def _engine() -> EnforcementEngine:
    """Create an engine loaded with the real sensor-config policies."""
    engine = EnforcementEngine()
    engine.update_policies([REAL_PII_POLICY, SECRETS_POLICY])
    return engine


# ===========================================================================
# ChatGPT JSON payload tests
# ===========================================================================


class TestChatGPTJsonEnforcement:
    """Simulate ChatGPT POST /backend-api/conversation payloads."""

    def _chatgpt_body(self, user_message: str) -> str:
        """Build a realistic ChatGPT request body."""
        return json.dumps({
            "action": "next",
            "messages": [{
                "id": "aaa-bbb-ccc",
                "author": {"role": "user"},
                "content": {
                    "content_type": "text",
                    "parts": [user_message],
                },
                "metadata": {},
            }],
            "parent_message_id": "xxx-yyy-zzz",
            "model": "gpt-4o",
            "timezone_offset_min": -330,
            "history_and_training_disabled": False,
        })

    def test_email_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("Please email me at john.doe@company.com about the project")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
            "com.google.Chrome",
        )
        assert action == "block", f"Expected block, got {action}"
        assert violation is not None
        assert violation.detected_type == "email"
        assert violation.host == "chatgpt.com"

    def test_email_redacted(self):
        engine = _engine()
        body = self._chatgpt_body("Send an invite to jane@acme.org and cc bob@acme.org")
        redacted, detected = engine.redact_pii(body)
        assert "jane@acme.org" not in redacted
        assert "bob@acme.org" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in detected
        # JSON must stay valid
        parsed = json.loads(redacted)
        assert "jane@acme.org" not in parsed["messages"][0]["content"]["parts"][0]

    def test_phone_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("Call me at 555-867-5309 for details")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_phone_redacted(self):
        engine = _engine()
        body = self._chatgpt_body("My number is +1-555-123-4567, reach me anytime")
        redacted, detected = engine.redact_pii(body)
        assert "+1-555-123-4567" not in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "phone" in detected

    def test_ssn_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("My social is 123-45-6789, use it for the form")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_ssn_redacted(self):
        engine = _engine()
        body = self._chatgpt_body("SSN: 123-45-6789")
        redacted, detected = engine.redact_pii(body)
        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted
        assert "ssn" in detected

    def test_credit_card_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("My card number is 4111-1111-1111-1111")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_credit_card_redacted(self):
        engine = _engine()
        body = self._chatgpt_body("Visa ending in 4111-1111-1111-1111")
        redacted, detected = engine.redact_pii(body)
        assert "4111-1111-1111-1111" not in redacted
        assert "[CREDIT_CARD_REDACTED]" in redacted
        assert "credit_card" in detected

    def test_api_key_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("Use this key: sk-abc1234567890abcdef")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "api_key"

    def test_aws_key_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("My AWS access key is AKIAIOSFODNN7EXAMPLE")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "aws_key"

    def test_private_key_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("Here is my key: -----BEGIN RSA PRIVATE KEY-----")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "private_key"

    def test_github_token_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body(
            "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"
        )
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "github_token"

    def test_ip_address_detected_and_blocked(self):
        engine = _engine()
        body = self._chatgpt_body("Connect to server at 192.168.1.100")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ip_address"

    def test_multiple_pii_types_all_redacted(self):
        engine = _engine()
        body = self._chatgpt_body(
            "Email john@test.com, phone 555-123-4567, "
            "SSN 123-45-6789, card 4111-1111-1111-1111"
        )
        redacted, detected = engine.redact_pii(body)
        assert "john@test.com" not in redacted
        assert "555-123-4567" not in redacted
        assert "123-45-6789" not in redacted
        assert "4111-1111-1111-1111" not in redacted
        # At least some of these should be detected
        assert len(detected) >= 2

    def test_clean_message_allowed(self):
        engine = _engine()
        body = self._chatgpt_body("What is the capital of France?")
        action, violation = engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "allow"
        assert violation is None

    def test_clean_message_not_redacted(self):
        engine = _engine()
        body = self._chatgpt_body("Explain quantum computing in simple terms")
        redacted, detected = engine.redact_pii(body)
        assert redacted == body
        assert detected == []


# ===========================================================================
# ChatGPT SSE streaming response tests
# ===========================================================================


class TestChatGPTSSEEnforcement:
    """Simulate SSE streaming data from ChatGPT responses, then enforce."""

    def test_sse_with_email_normalized_and_detected(self):
        """SSE stream containing email should be detected after normalization."""
        sse_bytes = (
            b'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"Contact "}}]}\n\n'
            b'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"john@example.com "}}]}\n\n'
            b'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"for details"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_sse_with_phone_detected(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"Call 555-123-4567"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_sse_with_ssn_detected(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"SSN is 123-45-6789"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_sse_with_credit_card_detected(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"Card: 4111-1111-1111-1111"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_sse_clean_content_allowed(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"The weather is nice today"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "allow"
        assert violation is None

    def test_sse_normalization_extracts_data_lines(self):
        """Verify SSE normalization concatenates data: lines properly."""
        sse_bytes = (
            b'data: {"a":"hello"}\n\n'
            b'data: {"b":"world"}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        assert '{"a":"hello"}' in normalized
        assert '{"b":"world"}' in normalized
        assert "[DONE]" not in normalized


# ===========================================================================
# Gemini protobuf/gRPC payload tests (simulated as decoded JSON)
# ===========================================================================


class TestGeminiProtobufEnforcement:
    """Simulate Gemini protobuf payloads.

    In production, Gemini sends protobuf data which gets decoded by
    normalize_grpc() into JSON. We test the enforcement on the decoded
    JSON representation, which is what check_request() receives.
    """

    def _gemini_decoded_json(self, user_text: str) -> str:
        """Build a Gemini-like decoded protobuf payload as JSON.

        This simulates what blackboxprotobuf.decode_message() produces
        for a Gemini StreamGenerate request.
        """
        return json.dumps({
            "1": {
                "1": {
                    "1": user_text,
                },
            },
            "2": {
                "1": "gemini-2.0-flash",
            },
            "4": {
                "1": 1,
                "2": 8192,
            },
        })

    def _gemini_nested_parts(self, parts: list[str]) -> str:
        """Build a Gemini multi-part decoded protobuf payload."""
        return json.dumps({
            "1": {
                "1": {
                    "1": [{"1": part} for part in parts],
                },
            },
            "2": {"1": "gemini-2.0-flash"},
        })

    def test_email_in_protobuf_detected(self):
        engine = _engine()
        body = self._gemini_decoded_json(
            "Send the report to alice@company.com"
        )
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_email_in_protobuf_redacted(self):
        engine = _engine()
        body = self._gemini_decoded_json("Email alice@corp.io for details")
        redacted, detected = engine.redact_pii(body)
        assert "alice@corp.io" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in detected

    def test_phone_in_protobuf_detected(self):
        engine = _engine()
        body = self._gemini_decoded_json("Call +1-800-555-0199 for support")
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_phone_in_protobuf_redacted(self):
        engine = _engine()
        body = self._gemini_decoded_json("My phone is (555) 987-6543")
        redacted, detected = engine.redact_pii(body)
        assert "(555) 987-6543" not in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "phone" in detected

    def test_ssn_in_protobuf_detected(self):
        engine = _engine()
        body = self._gemini_decoded_json("My SSN is 999-88-7777")
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_credit_card_in_protobuf_detected(self):
        engine = _engine()
        body = self._gemini_decoded_json("Card number: 5500-0000-0000-0004")
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_credit_card_in_protobuf_redacted(self):
        engine = _engine()
        body = self._gemini_decoded_json("My Visa is 4111-1111-1111-1111")
        redacted, detected = engine.redact_pii(body)
        assert "4111-1111-1111-1111" not in redacted
        assert "[CREDIT_CARD_REDACTED]" in redacted
        assert "credit_card" in detected

    def test_api_key_in_protobuf_detected(self):
        engine = _engine()
        body = self._gemini_decoded_json(
            "Use API key sk-proj1234567890abcdef to access the service"
        )
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "api_key"

    def test_clean_protobuf_allowed(self):
        engine = _engine()
        body = self._gemini_decoded_json("What is the meaning of life?")
        action, violation = engine.check_request(
            body, "gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate", "POST",
        )
        assert action == "allow"
        assert violation is None

    def test_multiple_pii_in_protobuf_parts_redacted(self):
        engine = _engine()
        body = self._gemini_nested_parts([
            "Email alice@test.com",
            "Phone 555-111-2222",
            "Card 4111-1111-1111-1111",
        ])
        redacted, detected = engine.redact_pii(body)
        assert "alice@test.com" not in redacted
        assert "555-111-2222" not in redacted
        assert "4111-1111-1111-1111" not in redacted
        assert len(detected) >= 2


# ===========================================================================
# Gemini anti-hijack prefixed response tests
# ===========================================================================


class TestGeminiAntiHijackEnforcement:
    """Simulate Gemini responses with )]}' anti-hijack prefix."""

    def test_anti_hijack_with_email_detected(self):
        """Gemini-style response with )]}' prefix containing email."""
        raw = (
            b")]}'\n"
            b'[["wrb.fr","XqKae","[\\"Contact alice@example.com for help\\"]",null,null,null,"generic"]]\n'
        )
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_anti_hijack_with_phone_detected(self):
        raw = (
            b")]}'\n"
            b'[["data","result","Call 555-123-4567 for info"]]\n'
        )
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_anti_hijack_clean_content_allowed(self):
        raw = (
            b")]}'\n"
            b'[["data","result","The weather is sunny today"]]\n'
        )
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "allow"
        assert violation is None


# ===========================================================================
# Gemini generativelanguage.googleapis.com JSON API tests
# ===========================================================================


class TestGeminiAPIJsonEnforcement:
    """Simulate Gemini API requests via generativelanguage.googleapis.com."""

    def _gemini_api_body(self, user_text: str) -> str:
        return json.dumps({
            "contents": [{
                "parts": [{"text": user_text}],
                "role": "user",
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._gemini_api_body("Forward to mike@startup.io please")
        action, violation = engine.check_request(
            body, "generativelanguage.googleapis.com",
            "/v1beta/models/gemini-2.0-flash:streamGenerateContent", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_email_redacted(self):
        engine = _engine()
        body = self._gemini_api_body("CC sarah@bigcorp.com on that thread")
        redacted, detected = engine.redact_pii(body)
        assert "sarah@bigcorp.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        parsed = json.loads(redacted)
        assert "sarah@bigcorp.com" not in parsed["contents"][0]["parts"][0]["text"]

    def test_ssn_detected(self):
        engine = _engine()
        body = self._gemini_api_body("My SSN is 456-78-9012")
        action, violation = engine.check_request(
            body, "generativelanguage.googleapis.com",
            "/v1beta/models/gemini-2.0-flash:streamGenerateContent", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._gemini_api_body("Translate this to French: Hello world")
        action, violation = engine.check_request(
            body, "generativelanguage.googleapis.com",
            "/v1beta/models/gemini-2.0-flash:streamGenerateContent", "POST",
        )
        assert action == "allow"
        assert violation is None


# ===========================================================================
# Claude API enforcement tests
# ===========================================================================


class TestClaudeEnforcement:
    """Simulate Claude API requests."""

    def _claude_body(self, user_text: str) -> str:
        return json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": user_text}
            ],
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._claude_body("Email admin@internal.net about the outage")
        action, violation = engine.check_request(
            body, "api.anthropic.com", "/v1/messages", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_phone_detected(self):
        engine = _engine()
        body = self._claude_body("My direct line is 408-555-0147")
        action, violation = engine.check_request(
            body, "api.anthropic.com", "/v1/messages", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._claude_body("What is recursion?")
        action, violation = engine.check_request(
            body, "api.anthropic.com", "/v1/messages", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Normalize → enforce integration tests
# ===========================================================================


class TestNormalizeToEnforcePipeline:
    """Full pipeline: raw bytes → normalize_body → check_request."""

    def test_json_bytes_with_email(self):
        """Raw JSON bytes → normalize → enforce."""
        raw = json.dumps({
            "messages": [{"content": "Mail bob@acme.com about the deal"}]
        }).encode("utf-8")
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_json_bytes_clean(self):
        raw = json.dumps({
            "messages": [{"content": "Tell me a joke"}]
        }).encode("utf-8")
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "allow"

    def test_sse_bytes_with_ssn(self):
        """Raw SSE bytes → normalize → enforce."""
        raw = (
            b'data: {"delta":{"content":"My SSN is 123-45-6789"}}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(raw, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_sse_bytes_with_credit_card(self):
        raw = (
            b'data: {"delta":{"content":"Card 4111-1111-1111-1111 on file"}}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(raw, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_anti_hijack_bytes_with_aws_key(self):
        raw = (
            b")]}'\n"
            b'{"result":"Use key AKIAIOSFODNN7EXAMPLE for S3"}\n'
        )
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block"
        assert violation.detected_type == "aws_key"


# ===========================================================================
# Redaction output format tests
# ===========================================================================


class TestRedactionOutputFormat:
    """Verify that redacted content uses correct placeholder labels."""

    def setup_method(self):
        self.engine = _engine()

    def test_email_placeholder(self):
        _, detected = self.engine.redact_pii("contact user@test.com now")
        assert "email" in detected

    def test_phone_placeholder(self):
        redacted, detected = self.engine.redact_pii("phone: 555-123-4567")
        assert "555-123-4567" not in redacted
        assert "phone" in detected

    def test_ssn_placeholder(self):
        redacted, detected = self.engine.redact_pii("ssn: 123-45-6789")
        assert "123-45-6789" not in redacted
        assert "ssn" in detected

    def test_credit_card_placeholder(self):
        redacted, detected = self.engine.redact_pii("card: 4111-1111-1111-1111")
        assert "4111-1111-1111-1111" not in redacted
        assert "credit_card" in detected

    def test_api_key_placeholder(self):
        redacted, detected = self.engine.redact_pii("key: sk-abc1234567890abcdef")
        assert "sk-abc1234567890abcdef" not in redacted
        assert "api_key" in detected

    def test_aws_key_placeholder(self):
        redacted, detected = self.engine.redact_pii("aws: AKIAIOSFODNN7EXAMPLE")
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "aws_key" in detected

    def test_private_key_placeholder(self):
        redacted, detected = self.engine.redact_pii(
            "key: -----BEGIN RSA PRIVATE KEY-----"
        )
        assert "-----BEGIN RSA PRIVATE KEY-----" not in redacted
        assert "private_key" in detected


# ===========================================================================
# Policy mode interaction tests
# ===========================================================================


class TestPolicyModeInteraction:
    """Test that different policy modes (block, warn, monitor) behave
    correctly with the same data across different services."""

    def test_warn_mode_blocks_first_then_allows_retry(self):
        """Warn mode: first request blocked, retry allowed."""
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Warn PII", "mode": "warn",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "Detect",
                "severity": "high", "dataTypes": ["email"],
            }],
        }])
        body = json.dumps({"contents": [{"parts": [{"text": "mail bob@test.com"}]}]})
        # First: warn (blocked)
        action1, v1 = engine.check_request(
            body, "generativelanguage.googleapis.com",
            "/v1/models/gemini:streamGenerateContent", "POST",
        )
        assert action1 == "warn"
        assert v1.retry_allowed is True
        # Retry: allowed (within TTL)
        action2, v2 = engine.check_request(
            body, "generativelanguage.googleapis.com",
            "/v1/models/gemini:streamGenerateContent", "POST",
        )
        assert action2 == "allow"
        assert v2 is None

    def test_block_mode_always_blocks(self):
        """Block mode: every request with PII is blocked, no retries."""
        engine = _engine()
        body = json.dumps({"messages": [{"content": "SSN: 123-45-6789"}]})
        for _ in range(3):
            action, violation = engine.check_request(
                body, "chatgpt.com", "/backend-api/conversation", "POST",
            )
            assert action == "block"
            assert violation.retry_allowed is False

    def test_monitor_mode_allows_but_detects(self):
        """Monitor mode: always allows, but still reports violations."""
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Monitor PII", "mode": "monitor",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "Detect",
                "severity": "high", "dataTypes": ["email", "phone", "ssn"],
            }],
        }])
        body = json.dumps({
            "contents": [{"parts": [{"text": "Email admin@corp.com SSN 123-45-6789"}]}]
        })
        action, violation = engine.check_request(
            body, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "allow"
        assert violation is not None  # Still detected

    def test_monitor_mode_does_not_redact(self):
        """Monitor mode policies should NOT trigger redaction."""
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Monitor Only", "mode": "monitor",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "Detect",
                "severity": "high", "dataTypes": ["email"],
            }],
        }])
        body = "Email me at alice@test.com"
        redacted, detected = engine.redact_pii(body)
        assert redacted == body  # Unchanged
        assert detected == []


# ===========================================================================
# False positive resistance tests
# ===========================================================================


class TestFalsePositiveResistance:
    """Ensure common non-PII patterns DON'T trigger enforcement."""

    def setup_method(self):
        self.engine = _engine()

    def test_plain_digits_not_ssn(self):
        """9-digit number without separators should NOT be SSN."""
        body = json.dumps({"session_id": "123456789"})
        action, _ = self.engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        # Should not trigger ssn (no separators)
        # May trigger other types depending on Presidio; at minimum, ssn should not match
        redacted, detected = self.engine.redact_pii(body)
        assert "ssn" not in detected

    def test_plain_digits_credit_card_behavior(self):
        """16-digit number without separators: behavior depends on backend.

        Presidio uses Luhn checksum validation, so a valid card number like
        4111111111111111 (test Visa) IS detected.  Fallback regex requires
        separators to avoid false positives on generic numeric IDs.
        """
        try:
            from mitmproxy.addons.oximy.enforcement import _presidio_available
        except ImportError:
            from enforcement import _presidio_available  # type: ignore[no-redef]
        body = json.dumps({"trace_id": "4111111111111111"})
        redacted, detected = self.engine.redact_pii(body)
        if _presidio_available:
            # Presidio catches it — Luhn checksum passes for this test card
            assert "credit_card" in detected
        else:
            # Regex requires separators — no match on plain digits
            assert "credit_card" not in detected

    def test_plain_digits_not_phone(self):
        """10-digit number without separators should NOT be phone."""
        body = json.dumps({"timestamp": "1708012345"})
        action, _ = self.engine.check_request(
            body, "chatgpt.com", "/backend-api/conversation", "POST",
        )
        redacted, detected = self.engine.redact_pii(body)
        assert "phone" not in detected

    def test_protobuf_field_numbers_not_pii(self):
        """Protobuf field numbers and numeric values should NOT trigger."""
        body = json.dumps({
            "1": {"1": "Hello world"},
            "2": {"1": "gemini-2.0-flash"},
            "4": {"1": 1, "2": 8192},
            "7": 1234567890,
        })
        action, violation = self.engine.check_request(
            body, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "allow"
        assert violation is None

    def test_analytics_numeric_ids_not_phone(self):
        """Analytics payloads with numeric fields should not false-positive."""
        body = json.dumps({
            "type": "autosuggest",
            "count": 42,
            "offset": 0,
            "limit": 10,
            "session": "abc123",
            "ts": 1708012345,
        })
        redacted, detected = self.engine.redact_pii(body)
        assert "phone" not in detected
        assert "ssn" not in detected


# ===========================================================================
# Cross-service consistency tests
# ===========================================================================


class TestCrossServiceConsistency:
    """Same PII content sent through different services should produce
    the same enforcement result."""

    def _check_all_services(self, pii_text: str, expected_type: str):
        """Send the same PII through ChatGPT, Gemini, and Claude paths."""
        engine = _engine()
        services = [
            (
                json.dumps({"messages": [{"content": {"parts": [pii_text]}}]}),
                "chatgpt.com", "/backend-api/conversation",
            ),
            (
                json.dumps({"1": {"1": {"1": pii_text}}}),
                "gemini.google.com",
                "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            ),
            (
                json.dumps({"contents": [{"parts": [{"text": pii_text}]}]}),
                "generativelanguage.googleapis.com",
                "/v1/models/gemini-2.0-flash:streamGenerateContent",
            ),
            (
                json.dumps({"messages": [{"role": "user", "content": pii_text}]}),
                "api.anthropic.com", "/v1/messages",
            ),
        ]

        for body, host, path in services:
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "block", (
                f"Expected block for {expected_type} on {host}, got {action}"
            )
            assert violation.detected_type == expected_type, (
                f"Expected {expected_type} on {host}, "
                f"got {violation.detected_type}"
            )
            # Reset the engine for each service (block mode doesn't cache,
            # but just to be safe)
            engine = _engine()

    def test_email_consistent(self):
        self._check_all_services("Contact user@example.com", "email")

    def test_ssn_consistent(self):
        self._check_all_services("SSN: 123-45-6789", "ssn")

    def test_credit_card_consistent(self):
        self._check_all_services("Card: 4111-1111-1111-1111", "credit_card")

    def test_phone_consistent(self):
        self._check_all_services("Call 555-123-4567", "phone")

    def test_api_key_consistent(self):
        self._check_all_services("Key: sk-abc1234567890abcdef", "api_key")

    def test_aws_key_consistent(self):
        self._check_all_services("AWS: AKIAIOSFODNN7EXAMPLE", "aws_key")


# ===========================================================================
# DeepSeek enforcement tests
# ===========================================================================


class TestDeepSeekEnforcement:
    """Simulate DeepSeek POST /api/v0/chat/completion payloads + SSE."""

    def _deepseek_body(self, user_text: str) -> str:
        return json.dumps({
            "message": user_text,
            "stream": True,
            "model_class": "deepseek_chat",
            "temperature": 0,
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._deepseek_body("Send to alice@acme.org")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_email_redacted(self):
        engine = _engine()
        body = self._deepseek_body("Forward to bob@corp.io please")
        redacted, detected = engine.redact_pii(body)
        assert "bob@corp.io" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in detected
        json.loads(redacted)  # Must stay valid JSON

    def test_phone_detected(self):
        engine = _engine()
        body = self._deepseek_body("Call me at 555-321-9876")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._deepseek_body("My social is 999-88-7777")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_credit_card_detected(self):
        engine = _engine()
        body = self._deepseek_body("Card: 5500-0000-0000-0004")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_api_key_detected(self):
        engine = _engine()
        body = self._deepseek_body("Use key sk-proj1234567890abcdef")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "api_key"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._deepseek_body("Explain Python decorators")
        action, violation = engine.check_request(
            body, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "allow"
        assert violation is None

    def test_sse_response_with_email(self):
        """DeepSeek SSE streaming response containing email."""
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"Contact admin@deepseek.ai"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":" for help"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_sse_response_with_ssn(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"SSN: 111-22-3333"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_sse_clean_allowed(self):
        sse_bytes = (
            b'data: {"choices":[{"delta":{"content":"Hello, how can I help?"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Perplexity enforcement tests
# ===========================================================================


class TestPerplexityEnforcement:
    """Simulate Perplexity SSE streaming via /rest/sse/perplexity_ask."""

    def test_sse_with_email_detected(self):
        sse_bytes = (
            b'event: message\n'
            b'data: {"text":"Reach out to jane@startup.com for onboarding"}\n\n'
            b'event: message\n'
            b'data: {"text":" and follow up."}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "www.perplexity.ai", "/rest/sse/perplexity_ask", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_sse_with_phone_detected(self):
        sse_bytes = (
            b'data: {"text":"Call the office at (800) 555-0100"}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "www.perplexity.ai", "/rest/sse/perplexity_ask", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_sse_with_credit_card_detected(self):
        sse_bytes = (
            b'data: {"text":"Card ending 4111-1111-1111-1111"}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "www.perplexity.ai", "/rest/sse/perplexity_ask", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_sse_clean_allowed(self):
        sse_bytes = (
            b'data: {"text":"The capital of Japan is Tokyo."}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "www.perplexity.ai", "/rest/sse/perplexity_ask", "POST",
        )
        assert action == "allow"

    def test_sse_with_aws_key_detected(self):
        sse_bytes = (
            b'data: {"text":"Your AWS key is AKIAIOSFODNN7EXAMPLE"}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "www.perplexity.ai", "/rest/sse/perplexity_ask", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "aws_key"


# ===========================================================================
# Grok (xAI) enforcement tests
# ===========================================================================


class TestGrokEnforcement:
    """Simulate Grok JSON payloads to grok.com."""

    def _grok_body(self, user_text: str) -> str:
        return json.dumps({
            "message": user_text,
            "modelSlug": "grok-3",
            "parentMessageId": "abc-123",
            "temporary": False,
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._grok_body("Email support@xai.com about access")
        action, violation = engine.check_request(
            body, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_phone_detected(self):
        engine = _engine()
        body = self._grok_body("Call me at 650-555-0199")
        action, violation = engine.check_request(
            body, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._grok_body("SSN 222-33-4444")
        action, violation = engine.check_request(
            body, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_credit_card_detected(self):
        engine = _engine()
        body = self._grok_body("Visa 4111-1111-1111-1111")
        action, violation = engine.check_request(
            body, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._grok_body("What happened in the news today?")
        action, violation = engine.check_request(
            body, "grok.com", "/api/rpc", "POST",
        )
        assert action == "allow"

    def test_email_redacted(self):
        engine = _engine()
        body = self._grok_body("Send to ceo@company.com")
        redacted, detected = engine.redact_pii(body)
        assert "ceo@company.com" not in redacted
        assert "email" in detected
        json.loads(redacted)


# ===========================================================================
# Microsoft Copilot enforcement tests
# ===========================================================================


class TestCopilotEnforcement:
    """Simulate Microsoft Copilot /c/api/chat payloads."""

    def _copilot_body(self, user_text: str) -> str:
        return json.dumps({
            "messages": [
                {"role": "user", "content": user_text}
            ],
            "source": "cib",
            "optionsSets": ["deepleo", "enable_debug_commands"],
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._copilot_body("Forward to sarah@microsoft.com")
        action, violation = engine.check_request(
            body, "copilot.microsoft.com", "/c/api/chat", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._copilot_body("My SSN is 333-44-5555")
        action, violation = engine.check_request(
            body, "copilot.microsoft.com", "/c/api/chat", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_credit_card_detected(self):
        engine = _engine()
        body = self._copilot_body("Card 5500-0000-0000-0004")
        action, violation = engine.check_request(
            body, "copilot.microsoft.com", "/c/api/chat", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._copilot_body("Summarize this Excel spreadsheet")
        action, violation = engine.check_request(
            body, "copilot.microsoft.com", "/c/api/chat", "POST",
        )
        assert action == "allow"

    def test_phone_redacted(self):
        engine = _engine()
        body = self._copilot_body("My number is +1-800-555-0199")
        redacted, detected = engine.redact_pii(body)
        assert "+1-800-555-0199" not in redacted
        assert "phone" in detected
        json.loads(redacted)


# ===========================================================================
# HuggingFace Chat enforcement tests
# ===========================================================================


class TestHuggingFaceEnforcement:
    """Simulate HuggingFace Chat /chat/conversation payloads."""

    def _hf_body(self, user_text: str) -> str:
        return json.dumps({
            "inputs": user_text,
            "parameters": {"max_new_tokens": 1024},
            "model": "meta-llama/Llama-3.3-70B-Instruct",
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._hf_body("Reach out to dev@huggingface.co")
        action, violation = engine.check_request(
            body, "huggingface.co", "/chat/conversation/abc123", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._hf_body("SSN: 444-55-6666")
        action, violation = engine.check_request(
            body, "huggingface.co", "/chat/conversation/abc123", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._hf_body("Explain attention mechanism in transformers")
        action, violation = engine.check_request(
            body, "huggingface.co", "/chat/conversation/abc123", "POST",
        )
        assert action == "allow"


# ===========================================================================
# OpenRouter enforcement tests
# ===========================================================================


class TestOpenRouterEnforcement:
    """Simulate OpenRouter /api/v1/responses payloads."""

    def _openrouter_body(self, user_text: str) -> str:
        return json.dumps({
            "model": "anthropic/claude-sonnet-4-20250514",
            "messages": [
                {"role": "user", "content": user_text}
            ],
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._openrouter_body("CC admin@openrouter.ai")
        action, violation = engine.check_request(
            body, "openrouter.ai", "/api/v1/responses", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_private_key_detected(self):
        engine = _engine()
        body = self._openrouter_body("-----BEGIN EC PRIVATE KEY-----")
        action, violation = engine.check_request(
            body, "openrouter.ai", "/api/v1/responses", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "private_key"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._openrouter_body("Compare GPT-4 and Claude 3.5")
        action, violation = engine.check_request(
            body, "openrouter.ai", "/api/v1/responses", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Replit GraphQL enforcement tests
# ===========================================================================


class TestReplitEnforcement:
    """Simulate Replit GraphQL payloads."""

    def _replit_graphql(self, user_text: str) -> str:
        return json.dumps({
            "operationName": "ReplitAIChat",
            "query": "mutation ReplitAIChat($input: AIInput!) { aiChat(input: $input) { text } }",
            "variables": {
                "input": {
                    "message": user_text,
                    "replId": "abc123",
                }
            },
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._replit_graphql("Send invite to dev@replit.com")
        action, violation = engine.check_request(
            body, "replit.com", "/graphql", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_api_key_detected(self):
        engine = _engine()
        body = self._replit_graphql("Use API key sk-test1234567890abcdef")
        action, violation = engine.check_request(
            body, "replit.com", "/graphql", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "api_key"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._replit_graphql("Fix the syntax error in main.py")
        action, violation = engine.check_request(
            body, "replit.com", "/graphql", "POST",
        )
        assert action == "allow"

    def test_email_redacted_preserves_graphql_structure(self):
        engine = _engine()
        body = self._replit_graphql("Email bob@replit.com about the bug")
        redacted, detected = engine.redact_pii(body)
        parsed = json.loads(redacted)
        assert "bob@replit.com" not in json.dumps(parsed)
        assert parsed["operationName"] == "ReplitAIChat"
        assert "email" in detected


# ===========================================================================
# Canva AI enforcement tests
# ===========================================================================


class TestCanvaEnforcement:
    """Simulate Canva AI generation payloads."""

    def _canva_body(self, prompt: str) -> str:
        return json.dumps({
            "prompt": prompt,
            "type": "ingredientgeneration",
            "options": {"style": "modern", "format": "presentation"},
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._canva_body("Create a slide with contact info: admin@canva.com")
        action, violation = engine.check_request(
            body, "www.canva.com", "/_ajax/ingredientgeneration", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_phone_detected(self):
        engine = _engine()
        body = self._canva_body("Add phone number 555-123-4567 to contact slide")
        action, violation = engine.check_request(
            body, "www.canva.com", "/_ajax/ingredientgeneration", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._canva_body("Create a sunset landscape wallpaper")
        action, violation = engine.check_request(
            body, "www.canva.com", "/_ajax/ingredientgeneration", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Raycast enforcement tests
# ===========================================================================


class TestRaycastEnforcement:
    """Simulate Raycast AI chat completion payloads."""

    def _raycast_body(self, user_text: str) -> str:
        return json.dumps({
            "messages": [{"role": "user", "content": user_text}],
            "model": "openai-gpt-4o",
            "provider": "openai",
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._raycast_body("Draft email to user@raycast.com")
        action, violation = engine.check_request(
            body, "backend.raycast.com", "/api/v1/ai/chat_completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_aws_key_detected(self):
        engine = _engine()
        body = self._raycast_body("Explain this AWS key: AKIAIOSFODNN7EXAMPLE")
        action, violation = engine.check_request(
            body, "backend.raycast.com", "/api/v1/ai/chat_completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "aws_key"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._raycast_body("What is the time in Tokyo?")
        action, violation = engine.check_request(
            body, "backend.raycast.com", "/api/v1/ai/chat_completions", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Conductor GraphQL enforcement tests
# ===========================================================================


class TestConductorEnforcement:
    """Simulate Conductor content generation payloads."""

    def _conductor_body(self, user_text: str) -> str:
        return json.dumps({
            "query": "mutation GenerateContent($input: ContentInput!) { generate(input: $input) { text } }",
            "variables": {"input": {"prompt": user_text}},
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._conductor_body("Include contact editor@conductor.com")
        action, violation = engine.check_request(
            body, "app.conductor.com", "/content-generation-gateway/generate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._conductor_body("SSN: 777-88-9999")
        action, violation = engine.check_request(
            body, "app.conductor.com", "/content-generation-gateway/generate", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._conductor_body("Write a blog post about SEO best practices")
        action, violation = engine.check_request(
            body, "app.conductor.com", "/content-generation-gateway/generate", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Granola SSE + JSON enforcement tests
# ===========================================================================


class TestGranolaEnforcement:
    """Simulate Granola AI chat-with-documents and streaming payloads."""

    def _granola_body(self, user_text: str) -> str:
        return json.dumps({
            "messages": [{"role": "user", "content": user_text}],
            "documentIds": ["doc-abc"],
        })

    def test_email_detected_json(self):
        engine = _engine()
        body = self._granola_body("CC notes to pm@granola.ai")
        action, violation = engine.check_request(
            body, "api.granola.ai", "/v1/chat-with-documents", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_sse_stream_with_phone(self):
        sse_bytes = (
            b'data: {"delta":"Call me at 415-555-0123"}\n\n'
            b'data: {"delta":" to discuss."}\n\n'
            b'data: [DONE]\n\n'
        )
        normalized = normalize_body(sse_bytes, "text/event-stream; charset=utf-8")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "stream.api.granola.ai", "/v1/llm-proxy-stream", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._granola_body("Summarize the meeting notes")
        action, violation = engine.check_request(
            body, "api.granola.ai", "/v1/chat-with-documents", "POST",
        )
        assert action == "allow"


# ===========================================================================
# M365 Copilot (Office/Substrate) enforcement tests
# ===========================================================================


class TestM365CopilotEnforcement:
    """Simulate Microsoft 365 Copilot requests via substrate.office.com."""

    def _m365_body(self, user_text: str) -> str:
        return json.dumps({
            "messages": [{"role": "user", "content": user_text}],
            "context": {"appId": "Word"},
        })

    def test_email_detected(self):
        engine = _engine()
        body = self._m365_body("Send the doc to cfo@bigcorp.com")
        action, violation = engine.check_request(
            body, "substrate.office.com", "/m365copilot/chat", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_ssn_detected(self):
        engine = _engine()
        body = self._m365_body("Employee SSN: 111-22-3333")
        action, violation = engine.check_request(
            body, "substrate.office.com", "/m365copilot/chat", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_clean_allowed(self):
        engine = _engine()
        body = self._m365_body("Rewrite this paragraph more concisely")
        action, violation = engine.check_request(
            body, "substrate.office.com", "/m365copilot/chat", "POST",
        )
        assert action == "allow"


# ===========================================================================
# Encoding path tests: gzip, URL-encoded, base64, msgpack
# ===========================================================================


class TestGzipEncodedEnforcement:
    """Test enforcement on gzip-compressed request bodies going through
    normalize_body → check_request pipeline."""

    def test_gzipped_json_with_email(self):
        payload = json.dumps({"message": "Contact user@test.com"}).encode()
        compressed = gzip.compress(payload)
        normalized = normalize_body(compressed, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_gzipped_json_with_ssn(self):
        payload = json.dumps({"content": "SSN: 123-45-6789"}).encode()
        compressed = gzip.compress(payload)
        normalized = normalize_body(compressed, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "chat.deepseek.com", "/api/v0/chat/completion", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_gzipped_json_clean(self):
        payload = json.dumps({"message": "Hello world"}).encode()
        compressed = gzip.compress(payload)
        normalized = normalize_body(compressed, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "allow"


class TestURLEncodedEnforcement:
    """Test enforcement on URL-encoded (form) request bodies."""

    def test_form_with_email(self):
        form_data = urllib.parse.urlencode({
            "prompt": "Send to alice@example.com",
            "model": "gpt-4",
        }).encode("utf-8")
        normalized = normalize_body(form_data, "application/x-www-form-urlencoded")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_form_with_phone(self):
        form_data = urllib.parse.urlencode({
            "message": "Call 555-123-4567",
        }).encode("utf-8")
        normalized = normalize_body(form_data, "application/x-www-form-urlencoded")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "phone"

    def test_form_clean(self):
        form_data = urllib.parse.urlencode({
            "prompt": "What is gravity?",
        }).encode("utf-8")
        normalized = normalize_body(form_data, "application/x-www-form-urlencoded")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "allow"


class TestBase64EncodedEnforcement:
    """Test enforcement on base64-encoded payloads going through
    normalize_body layered decoding."""

    def test_base64_json_with_email(self):
        payload = json.dumps({"msg": "Email dev@company.io please"}).encode()
        b64 = base64.b64encode(payload)
        normalized = normalize_body(b64, "application/octet-stream")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_base64_json_with_credit_card(self):
        payload = json.dumps({"msg": "Card 4111-1111-1111-1111"}).encode()
        b64 = base64.b64encode(payload)
        normalized = normalize_body(b64, "application/octet-stream")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "grok.com", "/api/rpc", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"

    def test_base64_clean(self):
        payload = json.dumps({"msg": "What is photosynthesis?"}).encode()
        b64 = base64.b64encode(payload)
        normalized = normalize_body(b64, "application/octet-stream")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "api.openai.com", "/v1/chat/completions", "POST",
        )
        assert action == "allow"


class TestMessagePackEnforcement:
    """Test enforcement on MessagePack-encoded payloads (used by Replit WS)."""

    def test_msgpack_with_email(self):
        try:
            import msgpack
        except ImportError:
            return  # Skip if msgpack not installed
        payload = {"message": "Send to admin@replit.com", "type": "chat"}
        packed = msgpack.packb(payload, use_bin_type=True)
        normalized = normalize_body(packed, "application/msgpack")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "production-chort.replit.com", "/ws", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_msgpack_with_ssn(self):
        try:
            import msgpack
        except ImportError:
            return
        payload = {"content": "SSN 999-88-7777", "event": "message"}
        packed = msgpack.packb(payload, use_bin_type=True)
        normalized = normalize_body(packed, "application/msgpack")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "production-chort.replit.com", "/ws", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "ssn"

    def test_msgpack_clean(self):
        try:
            import msgpack
        except ImportError:
            return
        payload = {"message": "Fix the loop", "type": "chat"}
        packed = msgpack.packb(payload, use_bin_type=True)
        normalized = normalize_body(packed, "application/msgpack")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "production-chort.replit.com", "/ws", "POST",
        )
        assert action == "allow"

    def test_msgpack_with_api_key(self):
        try:
            import msgpack
        except ImportError:
            return
        payload = {"text": "Here is my key: sk-proj1234567890abcdef"}
        packed = msgpack.packb(payload, use_bin_type=True)
        normalized = normalize_body(packed, "application/msgpack")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "production-chort.replit.com", "/ws", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "api_key"


# ===========================================================================
# Anti-hijack prefix variant tests
# ===========================================================================


class TestAntiHijackVariants:
    """Test all anti-JSON-hijacking prefix variants from normalize.py."""

    def _check_prefix(self, prefix: bytes, pii_text: str, expected_type: str):
        raw = prefix + json.dumps({"text": pii_text}).encode()
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block", (
            f"Expected block with prefix {prefix!r}, got {action}"
        )
        assert violation.detected_type == expected_type

    def test_google_prefix_with_email(self):
        self._check_prefix(b")]}'\n", "user@google.com", "email")

    def test_google_prefix_no_newline_with_ssn(self):
        self._check_prefix(b")]}'", "SSN: 123-45-6789", "ssn")

    def test_facebook_prefix_with_phone(self):
        self._check_prefix(b"for(;;);", "Call 555-123-4567", "phone")

    def test_while_prefix_with_credit_card(self):
        self._check_prefix(b"while(1);", "Card 4111-1111-1111-1111", "credit_card")

    def test_empty_object_prefix_with_email(self):
        self._check_prefix(b"{}&&", "contact admin@test.com", "email")


# ===========================================================================
# Gemini length-prefixed streaming (anti-hijack + chunked)
# ===========================================================================


class TestGeminiLengthPrefixedStream:
    """Gemini sometimes sends anti-hijack prefix + length-prefixed JSON chunks."""

    def test_length_prefixed_with_email(self):
        chunk = json.dumps({"result": "Email alice@google.com for info"})
        raw = (")]}'\n" + str(len(chunk)) + "\n" + chunk + "\n").encode()
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_multi_chunk_with_credit_card(self):
        chunk1 = json.dumps({"part": "Card is "})
        chunk2 = json.dumps({"part": "4111-1111-1111-1111"})
        raw = (")]}'\n" + str(len(chunk1)) + "\n" + chunk1 + "\n"
               + str(len(chunk2)) + "\n" + chunk2 + "\n").encode()
        normalized = normalize_body(raw, "application/json")
        engine = _engine()
        action, violation = engine.check_request(
            normalized, "gemini.google.com",
            "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate",
            "POST",
        )
        assert action == "block"
        assert violation.detected_type == "credit_card"


# ===========================================================================
# Expanded cross-service consistency (all services)
# ===========================================================================


class TestAllServiceConsistency:
    """Same PII routed through every whitelisted service domain — enforcement
    must block on every single one."""

    ALL_SERVICES = [
        ("chatgpt.com", "/backend-api/conversation"),
        ("gemini.google.com", "/$rpc/google.internal.communications.gemini.v1.GeminiService/StreamGenerate"),
        ("generativelanguage.googleapis.com", "/v1/models/gemini-2.0-flash:streamGenerateContent"),
        ("api.anthropic.com", "/v1/messages"),
        ("chat.deepseek.com", "/api/v0/chat/completion"),
        ("www.perplexity.ai", "/rest/sse/perplexity_ask"),
        ("grok.com", "/api/rpc"),
        ("copilot.microsoft.com", "/c/api/chat"),
        ("huggingface.co", "/chat/conversation/abc"),
        ("openrouter.ai", "/api/v1/responses"),
        ("replit.com", "/graphql"),
        ("www.canva.com", "/_ajax/ingredientgeneration"),
        ("backend.raycast.com", "/api/v1/ai/chat_completions"),
        ("app.conductor.com", "/content-generation-gateway/generate"),
        ("api.granola.ai", "/v1/chat-with-documents"),
        ("substrate.office.com", "/m365copilot/chat"),
        ("api.openai.com", "/v1/chat/completions"),
    ]

    def _wrap(self, text: str) -> str:
        return json.dumps({"messages": [{"content": text}]})

    def test_email_blocked_on_all_services(self):
        for host, path in self.ALL_SERVICES:
            engine = _engine()
            body = self._wrap("Contact user@example.com")
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "block", f"Email not blocked on {host}{path}"
            assert violation.detected_type == "email", f"Wrong type on {host}"

    def test_ssn_blocked_on_all_services(self):
        for host, path in self.ALL_SERVICES:
            engine = _engine()
            body = self._wrap("SSN: 123-45-6789")
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "block", f"SSN not blocked on {host}{path}"
            assert violation.detected_type == "ssn", f"Wrong type on {host}"

    def test_credit_card_blocked_on_all_services(self):
        for host, path in self.ALL_SERVICES:
            engine = _engine()
            body = self._wrap("Card: 4111-1111-1111-1111")
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "block", f"Credit card not blocked on {host}{path}"
            assert violation.detected_type == "credit_card", f"Wrong type on {host}"

    def test_phone_blocked_on_all_services(self):
        for host, path in self.ALL_SERVICES:
            engine = _engine()
            body = self._wrap("Call 555-123-4567")
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "block", f"Phone not blocked on {host}{path}"
            assert violation.detected_type == "phone", f"Wrong type on {host}"

    def test_clean_allowed_on_all_services(self):
        for host, path in self.ALL_SERVICES:
            engine = _engine()
            body = self._wrap("What is machine learning?")
            action, violation = engine.check_request(body, host, path, "POST")
            assert action == "allow", f"Clean text blocked on {host}{path}"
            assert violation is None


# ===========================================================================
# Detection method verification: Presidio vs fallback regex
# ===========================================================================


class TestDetectionMethod:
    """Verify which detection backend is active and document
    the detection_method field on violations.

    When Presidio is available the violation.detection_method will be
    one of: presidio_pattern, presidio_ner, presidio_custom.
    When Presidio is unavailable (fallback) it will be: fallback_regex.

    This class tests both paths explicitly so we know *how* PII was caught.
    """

    def test_detection_method_is_reported(self):
        """Every violation must carry a detection_method."""
        engine = _engine()
        _, violation = engine.check_request(
            "Email: test@example.com",
            "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert violation is not None
        assert violation.detection_method in (
            "presidio_pattern", "presidio_ner", "presidio_custom",
            "fallback_regex",
        ), f"Unexpected detection_method: {violation.detection_method}"

    def test_fallback_regex_types_always_detected(self):
        """These 9 types have fallback regex — they must be caught regardless
        of whether Presidio is available."""
        cases = [
            ("email", "Email: user@test.com"),
            ("phone", "Call 555-123-4567"),
            ("ssn", "SSN: 123-45-6789"),
            ("credit_card", "Card: 4111-1111-1111-1111"),
            ("api_key", "Key: sk-abc1234567890abcdef"),
            ("aws_key", "AWS: AKIAIOSFODNN7EXAMPLE"),
            ("github_token", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn"),
            ("ip_address", "Server: 192.168.1.100"),
            ("private_key", "-----BEGIN RSA PRIVATE KEY-----"),
        ]
        for expected_type, body in cases:
            engine = _engine()
            action, violation = engine.check_request(
                body, "chatgpt.com", "/backend-api/conversation", "POST",
            )
            assert action == "block", (
                f"{expected_type}: expected block, got {action}"
            )
            assert violation.detected_type == expected_type

    def test_person_name_requires_presidio(self):
        """person_name has NO fallback regex. When Presidio is unavailable,
        a person's name will pass through undetected.

        This is a known gap — NER-based detection requires the ML model.
        """
        from mitmproxy.addons.oximy.enforcement import _presidio_available
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Name Detection", "mode": "block",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "Names",
                "severity": "high", "dataTypes": ["person_name"],
            }],
        }])
        action, violation = engine.check_request(
            "Please contact John Smith about the project",
            "chatgpt.com", "/backend-api/conversation", "POST",
        )
        if _presidio_available:
            # Presidio should detect "John Smith"
            assert action == "block"
            assert violation.detected_type == "person_name"
            assert violation.detection_method == "presidio_ner"
        else:
            # No fallback regex for person_name — passes through
            assert action == "allow"
            assert violation is None

    def test_location_requires_presidio(self):
        """location is an NER-based type — requires Presidio, no fallback regex."""
        from mitmproxy.addons.oximy.enforcement import _presidio_available
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Location Detection", "mode": "block",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "Locations",
                "severity": "high", "dataTypes": ["location"],
            }],
        }])
        action, violation = engine.check_request(
            "I live at 123 Main Street, Springfield, IL",
            "chatgpt.com", "/backend-api/conversation", "POST",
        )
        if _presidio_available:
            assert action == "block"
            assert violation.detected_type == "location"
            assert violation.detection_method == "presidio_ner"
        else:
            # No fallback regex for NER-based types — passes through
            assert action == "allow"
            assert violation is None

    def test_mixed_policy_detects_fallback_types_even_without_presidio(self):
        """Real sensor-config has both regex-covered and Presidio-only types
        in the same rule. The regex-covered ones must still fire."""
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "Mixed PII", "mode": "block",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "All PII",
                "severity": "high",
                "dataTypes": [
                    "email", "phone", "ssn", "person_name", "location",
                    "credit_card", "api_key",
                ],
            }],
        }])

        # Email: always detected (has fallback regex)
        engine2 = EnforcementEngine()
        engine2.update_policies([{
            "id": "p1", "name": "Mixed PII", "mode": "block",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "All PII",
                "severity": "high",
                "dataTypes": [
                    "email", "phone", "ssn", "person_name", "location",
                    "credit_card", "api_key",
                ],
            }],
        }])
        action, violation = engine2.check_request(
            "Send to admin@test.com",
            "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert action == "block"
        assert violation.detected_type == "email"

    def test_confidence_score_is_set(self):
        """Violations must have a confidence_score > 0."""
        engine = _engine()
        _, violation = engine.check_request(
            "Email: test@example.com",
            "chatgpt.com", "/backend-api/conversation", "POST",
        )
        assert violation is not None
        assert violation.confidence_score > 0

    def test_redaction_with_mixed_types_only_redacts_regex_covered(self):
        """When Presidio is down, redact_pii only redacts the 9 types that
        have fallback patterns. Person names pass through unredacted."""
        from mitmproxy.addons.oximy.enforcement import _presidio_available
        engine = EnforcementEngine()
        engine.update_policies([{
            "id": "p1", "name": "All PII", "mode": "block",
            "rules": [{
                "id": "r1", "type": "data_type", "name": "PII",
                "severity": "high",
                "dataTypes": ["email", "person_name"],
            }],
        }])
        body = "Contact John Smith at john@example.com for details"
        redacted, detected = engine.redact_pii(body)
        # Email always redacted
        assert "john@example.com" not in redacted
        assert "email" in detected
        if not _presidio_available:
            # Without Presidio, "John Smith" is NOT redacted
            assert "John Smith" in redacted
            assert "person_name" not in detected
