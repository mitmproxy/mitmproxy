"""Integration tests for OximyAddon request/response pipeline.

Tests the real decision pipeline end-to-end using mock mitmproxy flow objects.
Covers: whitelist/blacklist filtering, app gating, TLS passthrough, config
parsing, and response → trace event generation.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from mitmproxy.addons.oximy.addon import (
    OximyAddon,
    TLSPassthrough,
    MemoryTraceBuffer,
    _parse_sensor_config,
    _state,
)
from mitmproxy.addons.oximy.process import ClientProcess


# =============================================================================
# Test Helpers
# =============================================================================


def _make_flow(
    host: str,
    path: str = "/",
    method: str = "GET",
    request_body: bytes | None = None,
    response_status: int = 200,
    response_body: bytes | None = None,
    response_content_type: str = "application/json",
    request_headers: dict | None = None,
    response_headers: dict | None = None,
    origin: str | None = None,
    referer: str | None = None,
    client_conn_id: str = "test-conn-1",
) -> MagicMock:
    """Create a mock mitmproxy HTTPFlow for integration testing."""
    flow = MagicMock()
    flow.metadata = {}

    # Request
    flow.request.pretty_host = host
    flow.request.path = path
    flow.request.method = method
    flow.request.url = f"https://{host}{path}"
    flow.request.content = request_body
    flow.request.timestamp_start = time.time()

    req_headers = dict(request_headers or {})
    if origin:
        req_headers["origin"] = origin
    if referer:
        req_headers["referer"] = referer

    # Make headers behave like mitmproxy Headers (dict-like with .get and .items)
    flow.request.headers = MagicMock()
    flow.request.headers.get = lambda k, d="": req_headers.get(k, d)
    flow.request.headers.items = lambda: req_headers.items()
    flow.request.headers.__iter__ = lambda self: iter(req_headers)

    # Response
    flow.response = MagicMock()
    flow.response.status_code = response_status
    flow.response.content = response_body or b'{"ok": true}'
    flow.response.timestamp_start = time.time()
    flow.response.timestamp_end = time.time() + 0.1

    resp_headers = {"content-type": response_content_type}
    if response_headers:
        resp_headers.update(response_headers)

    flow.response.headers = MagicMock()
    flow.response.headers.get = lambda k, d="": resp_headers.get(k, d)
    flow.response.headers.items = lambda: resp_headers.items()

    # Client connection
    flow.client_conn = MagicMock()
    flow.client_conn.id = client_conn_id
    flow.client_conn.peername = ("127.0.0.1", 54321)

    # WebSocket (not a WS flow by default)
    flow.websocket = None

    return flow


def _make_addon(
    whitelist: list[str] | None = None,
    blacklist: list[str] | None = None,
    allowed_app_hosts: list[str] | None = None,
    allowed_app_non_hosts: list[str] | None = None,
    allowed_host_origins: list[str] | None = None,
    apps_with_parsers: list[str] | None = None,
    passthrough_patterns: list[str] | None = None,
    client_processes: dict[str, ClientProcess] | None = None,
) -> OximyAddon:
    """Create a minimally-initialized OximyAddon with specific config for testing."""
    addon = object.__new__(OximyAddon)

    # Core state
    addon._enabled = True
    addon._fail_open_passthrough = False

    # Filtering config
    addon._whitelist = whitelist or []
    addon._blacklist = blacklist or []

    # App origin lists
    hosts = allowed_app_hosts or []
    non_hosts = allowed_app_non_hosts or []
    addon._allowed_app_hosts = hosts
    addon._allowed_app_hosts_set = {h.lower() for h in hosts}
    addon._allowed_app_non_hosts = non_hosts
    addon._allowed_app_non_hosts_set = {h.lower() for h in non_hosts}
    addon._allowed_host_origins = allowed_host_origins or []
    addon._apps_with_parsers = {p.lower() for p in (apps_with_parsers or [])}

    # No-parser caches
    addon._no_parser_apps_cache = {}
    addon._no_parser_apps_lock = threading.Lock()
    addon._no_parser_domains_cache = {}
    addon._no_parser_domains_lock = threading.Lock()

    # TLS
    if passthrough_patterns is not None:
        with patch.object(Path, "exists", return_value=False):
            addon._tls = TLSPassthrough(passthrough_patterns)
    else:
        addon._tls = None

    # Tracing (disabled for request-only tests)
    addon._buffer = None
    addon._direct_uploader = None
    addon._writer = None
    addon._debug_writer = None
    addon._uploader = None
    addon._device_id = "test-device"
    addon._output_dir = None
    addon._last_upload_time = 0
    addon._traces_since_upload = 0
    addon._upload_interval_seconds = 60
    addon._upload_threshold_count = 10
    addon._debug_ingestion = False
    addon._filename_pattern = "traces_{date}.jsonl"

    # Process resolver (disabled — we inject client_processes directly)
    addon._resolver = None
    addon._client_processes = client_processes or {}

    # Local data collector (disabled for tests)
    addon._local_collector = None

    # Enforcement rules (empty by default for tests)
    addon._enforcement_rules = []
    addon._blocked_domains = {}
    addon._warned_domains = {}
    addon._warned_web_sessions = set()

    return addon


CHROME = ClientProcess(
    pid=1234, name="Google Chrome", path="/Applications/Google Chrome.app",
    ppid=1, parent_name="launchd", user="test", port=54321,
    bundle_id="com.google.Chrome",
)

CHATGPT = ClientProcess(
    pid=2345, name="ChatGPT", path="/Applications/ChatGPT.app",
    ppid=1, parent_name="launchd", user="test", port=54321,
    bundle_id="com.openai.ChatGPT",
)

UNKNOWN_APP = ClientProcess(
    pid=3456, name="RandomApp", path="/Applications/RandomApp.app",
    ppid=1, parent_name="launchd", user="test", port=54321,
    bundle_id="com.random.App",
)

CURSOR = ClientProcess(
    pid=4567, name="Cursor", path="/Applications/Cursor.app",
    ppid=1, parent_name="launchd", user="test", port=54321,
    bundle_id="com.todesktop.cursor",
)


# =============================================================================
# Request Filter Pipeline Tests
# =============================================================================


class TestRequestFilterPipeline:
    """Tests for the request() handler's multi-step decision chain."""

    @pytest.fixture(autouse=True)
    def enable_sensor(self):
        """Ensure sensor is active for all tests."""
        original = _state.sensor_active
        _state.sensor_active = True
        yield
        _state.sensor_active = original

    @pytest.mark.asyncio
    async def test_whitelisted_request_marked_for_capture(self):
        """Whitelisted domain + known browser → oximy_capture = True."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["chatgpt.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            origin="https://chatgpt.com",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_capture") is True
        assert "oximy_skip" not in flow.metadata

    @pytest.mark.asyncio
    async def test_non_whitelisted_request_skipped(self):
        """Non-whitelisted domain → skipped with reason."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(host="random.com", path="/api/data")

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "not_whitelisted"

    @pytest.mark.asyncio
    async def test_whitelisted_but_blacklisted_url_skipped(self):
        """Whitelisted domain but URL contains blacklisted word → skipped."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            blacklist=["analytics"],
            allowed_app_hosts=["com.google.Chrome"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(host="api.openai.com", path="/v1/analytics")

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "blacklisted"

    @pytest.mark.asyncio
    async def test_graphql_operation_blacklisted(self):
        """GraphQL endpoint with blacklisted operation → skipped."""
        body = json.dumps({"operationName": "IntrospectionQuery", "query": "..."}).encode()
        addon = _make_addon(
            whitelist=["api.example.com"],
            blacklist=["introspectionquery"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["example.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="api.example.com",
            path="/graphql",
            method="POST",
            request_body=body,
            origin="https://example.com",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "blacklisted_graphql"

    @pytest.mark.asyncio
    async def test_path_pattern_whitelist_match(self):
        """URL with path pattern match → captured."""
        addon = _make_addon(
            whitelist=["gemini.google.com/**/StreamGenerate*"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["gemini.google.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="gemini.google.com",
            path="/v1/models/StreamGenerateContent",
            origin="https://gemini.google.com",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_capture") is True

    @pytest.mark.asyncio
    async def test_path_pattern_whitelist_no_match(self):
        """URL with path pattern but no match → skipped."""
        addon = _make_addon(
            whitelist=["gemini.google.com/**/StreamGenerate*"],
            allowed_app_hosts=["com.google.Chrome"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="gemini.google.com",
            path="/v1/models/ListModels",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "not_whitelisted"


# =============================================================================
# App Gating + Discovery Tests
# =============================================================================


class TestAppGating:
    """Tests for app gating (STEP 0) and discovery rate limiting."""

    @pytest.fixture(autouse=True)
    def enable_sensor(self):
        original = _state.sensor_active
        _state.sensor_active = True
        yield
        _state.sensor_active = original

    @pytest.mark.asyncio
    async def test_unknown_app_skipped(self):
        """App not in any allowed list → skipped."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_app_non_hosts=["com.openai.ChatGPT"],
            client_processes={"test-conn-1": UNKNOWN_APP},
        )
        flow = _make_flow(host="api.openai.com", path="/v1/chat/completions")

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "app_not_allowed"

    @pytest.mark.asyncio
    async def test_browser_app_passes_gating(self):
        """Browser app in allowed_app_hosts → proceeds to whitelist check."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["chatgpt.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            origin="https://chatgpt.com",
        )

        await addon.request(flow)

        # Browser passes gating, then whitelisted domain → captured
        assert flow.metadata.get("oximy_capture") is True
        assert flow.metadata.get("oximy_app_type") == "host"

    @pytest.mark.asyncio
    async def test_no_parser_app_first_request_metadata_only(self):
        """Non-browser app without parser, first request today → metadata-only discovery."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_app_non_hosts=["com.todesktop.cursor"],
            apps_with_parsers=[],  # Cursor has no parser
            client_processes={"test-conn-1": CURSOR},
        )
        flow = _make_flow(host="some-api.example.com", path="/v1/completions")

        with patch("mitmproxy.addons.oximy.addon._save_no_parser_apps_cache"):
            await addon.request(flow)

        assert flow.metadata.get("oximy_discovery_capture") is True
        assert flow.metadata.get("oximy_metadata_only") is True

    @pytest.mark.asyncio
    async def test_no_parser_app_second_request_rate_limited(self):
        """Non-browser app without parser, already seen today → skipped."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_app_non_hosts=["com.todesktop.cursor"],
            apps_with_parsers=[],
            client_processes={"test-conn-1": CURSOR},
        )
        # Pre-populate cache to simulate "already seen today"
        today = date.today().isoformat()
        addon._no_parser_apps_cache = {
            "date": today,
            "apps": {"com.todesktop.cursor": True},
        }

        flow = _make_flow(host="some-api.example.com", path="/v1/completions")

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "app_rate_limited"

    @pytest.mark.asyncio
    async def test_no_bundle_id_skipped(self):
        """Flow with no resolved process → skipped on macOS, captured on Windows."""
        import sys
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            client_processes={},  # No process mapping
        )
        flow = _make_flow(host="api.openai.com", path="/v1/chat")

        await addon.request(flow)

        if sys.platform == "win32":
            # On Windows, bundle_id=None falls through to domain-based filtering
            # instead of skipping, so whitelisted domains are still captured
            assert flow.metadata.get("oximy_skip") is not True
        else:
            assert flow.metadata.get("oximy_skip") is True
            assert flow.metadata.get("oximy_skip_reason") == "no_bundle_id"


# =============================================================================
# Host Origin Check Tests
# =============================================================================


class TestHostOriginCheck:
    """Tests for the host origin filter (STEP 6) for browser apps."""

    @pytest.fixture(autouse=True)
    def enable_sensor(self):
        original = _state.sensor_active
        _state.sensor_active = True
        yield
        _state.sensor_active = original

    @pytest.mark.asyncio
    async def test_browser_with_valid_origin_captured(self):
        """Browser with origin in allowed_host_origins → captured."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["chatgpt.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            origin="https://chatgpt.com",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_capture") is True
        assert flow.metadata.get("oximy_host_origin") == "chatgpt.com"

    @pytest.mark.asyncio
    async def test_browser_with_invalid_origin_skipped(self):
        """Browser with origin NOT in allowed_host_origins → skipped."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["chatgpt.com"],
            client_processes={"test-conn-1": CHROME},
        )
        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            origin="https://malicious-site.com",
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_skip") is True
        assert flow.metadata.get("oximy_skip_reason") == "host_origin_not_allowed"

    @pytest.mark.asyncio
    async def test_non_host_app_bypasses_origin_check(self):
        """Non-browser app (non_host) skips host origin check entirely."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_app_non_hosts=["com.openai.ChatGPT"],
            apps_with_parsers=["com.openai.ChatGPT"],
            allowed_host_origins=["chatgpt.com"],  # Only applies to browsers
            client_processes={"test-conn-1": CHATGPT},
        )
        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            # No origin header — native app
        )

        await addon.request(flow)

        assert flow.metadata.get("oximy_capture") is True
        assert flow.metadata.get("oximy_app_type") == "non_host"


# =============================================================================
# Config Parsing Tests
# =============================================================================


class TestConfigParsing:
    """Tests for _parse_sensor_config parsing the API response."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset global state between tests."""
        original_prev = _state.previous_sensor_enabled
        original_active = _state.sensor_active
        _state.previous_sensor_enabled = None
        yield
        _state.previous_sensor_enabled = original_prev
        _state.sensor_active = original_active

    @patch("mitmproxy.addons.oximy.addon._apply_sensor_state")
    @patch("mitmproxy.addons.oximy.addon._post_command_results_immediate")
    def test_parse_sensor_config_extracts_whitelist(self, mock_post, mock_apply):
        """Whitelist from API response is extracted correctly."""
        raw = {
            "data": {
                "whitelistedDomains": ["api.openai.com", "*.anthropic.com", "gemini.google.com/**/StreamGenerate*"],
                "blacklistedWords": ["analytics", "tracking"],
                "passthroughDomains": ["^.*\\.apple\\.com$"],
                "allowed_app_origins": {
                    "hosts": ["com.google.Chrome"],
                    "non_hosts": ["com.openai.ChatGPT"],
                    "apps_with_parsers": ["com.openai.chatgpt"],
                },
                "allowed_host_origins": ["chatgpt.com", "claude.ai"],
            }
        }

        with patch("builtins.open", mock_open()):
            with patch.object(Path, "mkdir"):
                with patch.object(Path, "parent", new_callable=lambda: property(lambda self: MagicMock())):
                    result = _parse_sensor_config(raw)

        assert result["whitelist"] == ["api.openai.com", "*.anthropic.com", "gemini.google.com/**/StreamGenerate*"]
        assert result["blacklist"] == ["analytics", "tracking"]
        assert result["passthrough"] == ["^.*\\.apple\\.com$"]
        assert result["allowed_app_origins"]["hosts"] == ["com.google.Chrome"]
        assert result["allowed_app_origins"]["non_hosts"] == ["com.openai.ChatGPT"]
        assert result["allowed_host_origins"] == ["chatgpt.com", "claude.ai"]

    @patch("mitmproxy.addons.oximy.addon._apply_sensor_state")
    @patch("mitmproxy.addons.oximy.addon._post_command_results_immediate")
    def test_parse_sensor_config_sensor_disabled(self, mock_post, mock_apply):
        """sensor_enabled=false should trigger _apply_sensor_state(False)."""
        raw = {
            "data": {
                "whitelistedDomains": [],
                "commands": {"sensor_enabled": False},
            }
        }

        with patch("builtins.open", mock_open()):
            with patch.object(Path, "mkdir"):
                with patch.object(Path, "parent", new_callable=lambda: property(lambda self: MagicMock())):
                    _parse_sensor_config(raw)

        # First call (previous_sensor_enabled is None) applies immediately
        mock_apply.assert_called_once_with(False, None)

    @patch("mitmproxy.addons.oximy.addon._apply_sensor_state")
    @patch("mitmproxy.addons.oximy.addon._post_command_results_immediate")
    def test_parse_sensor_config_empty_data_uses_defaults(self, mock_post, mock_apply):
        """Missing fields should fall back to empty defaults."""
        raw = {"data": {}}

        with patch("builtins.open", mock_open()):
            with patch.object(Path, "mkdir"):
                with patch.object(Path, "parent", new_callable=lambda: property(lambda self: MagicMock())):
                    result = _parse_sensor_config(raw)

        assert result["whitelist"] == []
        assert result["blacklist"] == []
        assert result["passthrough"] == []
        assert result["allowed_host_origins"] == []


# =============================================================================
# TLS Passthrough Tests
# =============================================================================


class TestTLSPassthroughIntegration:
    """Tests for tls_clienthello() passthrough decisions."""

    @pytest.fixture(autouse=True)
    def enable_sensor(self):
        original = _state.sensor_active
        _state.sensor_active = True
        yield
        _state.sensor_active = original

    def _make_client_hello(self, sni: str) -> MagicMock:
        """Create a mock ClientHelloData."""
        data = MagicMock()
        data.client_hello.sni = sni
        data.ignore_connection = False
        data.context.server.address = (sni, 443)
        data.context.client.id = "test-conn-1"
        return data

    def test_tls_whitelisted_domain_intercepted(self):
        """Whitelisted domain → TLS intercepted (NOT passed through)."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            passthrough_patterns=[],
        )
        data = self._make_client_hello("api.openai.com")

        addon.tls_clienthello(data)

        assert data.ignore_connection is False  # Intercepted

    def test_tls_non_whitelisted_domain_passthrough(self):
        """Non-whitelisted domain → TLS passed through (no interception)."""
        addon = _make_addon(
            whitelist=["api.openai.com"],
            passthrough_patterns=[],
        )
        data = self._make_client_hello("random.com")

        addon.tls_clienthello(data)

        assert data.ignore_connection is True  # Passed through

    def test_tls_cert_pinned_domain_passthrough(self):
        """Cert-pinned domain (in passthrough patterns) → passed through even if whitelisted."""
        addon = _make_addon(
            whitelist=["pinned.example.com"],
            passthrough_patterns=["^pinned\\.example\\.com$"],
        )
        data = self._make_client_hello("pinned.example.com")

        addon.tls_clienthello(data)

        # Whitelisted BUT cert-pinned → passthrough wins
        assert data.ignore_connection is True

    def test_tls_sensor_disabled_passthrough_all(self):
        """Sensor disabled → ALL connections passed through."""
        _state.sensor_active = False
        addon = _make_addon(
            whitelist=["api.openai.com"],
            passthrough_patterns=[],
        )
        data = self._make_client_hello("api.openai.com")

        addon.tls_clienthello(data)

        assert data.ignore_connection is True


# =============================================================================
# Response → Trace Event Tests
# =============================================================================


class TestResponseTraceEvent:
    """Tests for the response() handler producing trace events."""

    @pytest.fixture(autouse=True)
    def enable_sensor(self):
        original = _state.sensor_active
        _state.sensor_active = True
        yield
        _state.sensor_active = original

    def test_full_capture_produces_http_event(self):
        """Captured flow with response → event written to buffer."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            allowed_host_origins=["chatgpt.com"],
            client_processes={"test-conn-1": CHROME},
        )
        addon._buffer = buffer

        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            method="POST",
            request_body=b'{"model": "gpt-4"}',
            response_body=b'{"choices": [{"message": {"content": "Hello"}}]}',
            response_content_type="application/json",
            origin="https://chatgpt.com",
        )
        # Pre-mark as captured (normally done by request())
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_client"] = CHROME
        flow.metadata["oximy_app_type"] = "host"
        flow.metadata["oximy_host_origin"] = "chatgpt.com"

        addon.response(flow)

        assert buffer.size() == 1
        events = buffer.peek_all()
        event = events[0]
        assert event["type"] == "http"
        assert event["request"]["host"] == "api.openai.com"
        assert event["request"]["path"] == "/v1/chat/completions"
        assert event["request"]["method"] == "POST"
        assert event["response"]["status_code"] == 200
        assert event["device_id"] == "test-device"
        assert "event_id" in event
        assert "timestamp" in event

    def test_skipped_flow_not_traced(self):
        """Flow marked oximy_skip → response handler exits early, no trace."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
        addon = _make_addon(whitelist=["api.openai.com"])
        addon._buffer = buffer

        flow = _make_flow(host="random.com", path="/api")
        flow.metadata["oximy_skip"] = True
        flow.metadata["oximy_skip_reason"] = "not_whitelisted"

        addon.response(flow)

        assert buffer.size() == 0

    def test_metadata_only_produces_app_metadata_event(self):
        """Metadata-only flow → lightweight app_metadata event."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
        addon = _make_addon(
            whitelist=[],
            allowed_app_non_hosts=["com.todesktop.cursor"],
            client_processes={"test-conn-1": CURSOR},
        )
        addon._buffer = buffer

        flow = _make_flow(host="some-api.example.com", path="/v1/completions")
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_discovery_capture"] = True
        flow.metadata["oximy_metadata_only"] = True
        flow.metadata["oximy_client"] = CURSOR
        flow.metadata["oximy_app_type"] = "non_host"

        addon.response(flow)

        assert buffer.size() == 1
        events = buffer.peek_all()
        event = events[0]
        assert event["type"] == "app_metadata"
        assert event["request"]["host"] == "some-api.example.com"
        assert event["request"]["method"] == "GET"
        # app_metadata events should NOT have response body
        assert "response" not in event

    def test_streamed_sse_response_reassembled(self):
        """Streamed SSE chunks → reassembled and normalized."""
        buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
        addon = _make_addon(
            whitelist=["api.openai.com"],
            allowed_app_hosts=["com.google.Chrome"],
            client_processes={"test-conn-1": CHROME},
        )
        addon._buffer = buffer

        flow = _make_flow(
            host="api.openai.com",
            path="/v1/chat/completions",
            response_content_type="text/event-stream",
        )
        flow.metadata["oximy_capture"] = True
        flow.metadata["oximy_client"] = CHROME
        flow.metadata["oximy_app_type"] = "host"
        # Simulate streamed chunks
        flow.metadata["oximy_stream_chunks"] = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            b'data: [DONE]\n\n',
        ]

        addon.response(flow)

        assert buffer.size() == 1
        events = buffer.peek_all()
        event = events[0]
        assert event["type"] == "http"
        # The response body should contain the reassembled SSE content
        assert event["response"]["body"] is not None


# =============================================================================
# Sensor Disabled Tests
# =============================================================================


class TestSensorDisabled:
    """Tests that verify sensor disabled state skips all processing."""

    @pytest.mark.asyncio
    async def test_request_returns_early_when_sensor_disabled(self):
        """Sensor disabled → request() returns immediately, no metadata set."""
        original = _state.sensor_active
        _state.sensor_active = False
        try:
            addon = _make_addon(
                whitelist=["api.openai.com"],
                allowed_app_hosts=["com.google.Chrome"],
                client_processes={"test-conn-1": CHROME},
            )
            flow = _make_flow(host="api.openai.com", path="/v1/chat")

            await addon.request(flow)

            # No metadata should be set — handler returned early
            assert "oximy_capture" not in flow.metadata
            assert "oximy_skip" not in flow.metadata
        finally:
            _state.sensor_active = original

    def test_response_returns_early_when_sensor_disabled(self):
        """Sensor disabled → response() returns immediately."""
        original = _state.sensor_active
        _state.sensor_active = False
        try:
            buffer = MemoryTraceBuffer(max_bytes=1024 * 1024, max_count=100)
            addon = _make_addon(whitelist=["api.openai.com"])
            addon._buffer = buffer

            flow = _make_flow(host="api.openai.com", path="/v1/chat")
            flow.metadata["oximy_capture"] = True

            addon.response(flow)

            assert buffer.size() == 0
        finally:
            _state.sensor_active = original
