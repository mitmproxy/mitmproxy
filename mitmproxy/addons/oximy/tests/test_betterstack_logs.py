"""Tests for Better Stack Logs integration in oximy_logger.py.

Verifies batching, HTTP sending, proxy bypass, payload structure,
fail-open behavior, and INFO+ level gating.
"""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock, patch, ANY

import pytest

from mitmproxy.addons.oximy import oximy_logger
from mitmproxy.addons.oximy.oximy_logger import EventCode, _OximyLogger


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset module-level logger singleton between tests."""
    original = oximy_logger._logger
    oximy_logger._logger = _OximyLogger()
    yield oximy_logger._logger
    oximy_logger._logger = original


@pytest.fixture()
def configured_logger(reset_logger):
    """Return a logger instance with Better Stack configured."""
    lgr = reset_logger
    lgr.set_context(
        device_id="dev-123",
        workspace_id="ws-456",
        workspace_name="Acme",
        tenant_id="tenant-789",
    )
    return lgr


class TestBetterStackLogsGating:
    """Verify that logs are only sent when token/host are configured and level is INFO+."""

    def test_no_token_skips_sending(self, configured_logger):
        """Should not enqueue when BETTERSTACK_LOGS_TOKEN is empty."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", ""), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"):
            configured_logger._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "test", None, None, "2025-01-01T00:00:00.000Z"
            )
            assert len(configured_logger._bs_buffer) == 0

    def test_no_host_skips_sending(self, configured_logger):
        """Should not enqueue when BETTERSTACK_LOGS_HOST is empty."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", ""):
            configured_logger._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "test", None, None, "2025-01-01T00:00:00.000Z"
            )
            assert len(configured_logger._bs_buffer) == 0

    def test_debug_level_skipped(self, configured_logger):
        """Debug-level events should not be sent to Better Stack Logs."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"):
            # CFG_CB_003 is info level, let's find a debug-level event or test the gate directly
            # There's no debug EventCode, so test the level check path by mocking
            mock_code = MagicMock()
            mock_code.value = ("TEST.DBG.001", "debug", "none")
            configured_logger._send_to_betterstack_logs(
                mock_code, "debug msg", None, None, "2025-01-01T00:00:00.000Z"
            )
            assert len(configured_logger._bs_buffer) == 0

    def test_info_level_enqueued(self, configured_logger):
        """INFO-level events should be enqueued."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "started", None, None, "2025-01-01T00:00:00.000Z"
            )
            mock_enqueue.assert_called_once()

    def test_warning_level_enqueued(self, configured_logger):
        """Warning-level events should be enqueued."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.CFG_FAIL_201, "config fail", None, None, "2025-01-01T00:00:00.000Z"
            )
            mock_enqueue.assert_called_once()

    def test_error_level_enqueued(self, configured_logger):
        """Error-level events should be enqueued."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.CFG_FAIL_205, "error", None, None, "2025-01-01T00:00:00.000Z"
            )
            mock_enqueue.assert_called_once()


class TestPayloadStructure:
    """Verify the structure of entries sent to Better Stack Logs."""

    def test_entry_contains_required_fields(self, configured_logger):
        """Entry should contain dt, level, code, svc, op, msg, action, component."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "started",
                {"key": "val"}, {"code": "E001"},
                "2025-01-01T12:00:00.000Z"
            )
            entry = mock_enqueue.call_args[0][0]
            assert entry["dt"] == "2025-01-01T12:00:00.000Z"
            assert entry["level"] == "info"
            assert entry["code"] == "APP.INIT.001"
            assert entry["svc"] == "app"
            assert entry["op"] == "init"
            assert entry["msg"] == "started"
            assert entry["action"] == "none"
            assert entry["component"] == "python"

    def test_entry_includes_context_fields(self, configured_logger):
        """Entry should include device_id, workspace_id, workspace_name, tenant_id."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "started", None, None,
                "2025-01-01T12:00:00.000Z"
            )
            entry = mock_enqueue.call_args[0][0]
            assert entry["device_id"] == "dev-123"
            assert entry["workspace_id"] == "ws-456"
            assert entry["workspace_name"] == "Acme"
            assert entry["tenant_id"] == "tenant-789"

    def test_entry_includes_data_and_err(self, configured_logger):
        """Entry should include data and err dicts when provided."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_enqueue") as mock_enqueue:
            configured_logger._send_to_betterstack_logs(
                EventCode.UPLOAD_FAIL_201, "upload failed",
                {"bytes": 1024}, {"code": "TIMEOUT"},
                "2025-01-01T12:00:00.000Z"
            )
            entry = mock_enqueue.call_args[0][0]
            assert entry["data"] == {"bytes": 1024}
            assert entry["err"] == {"code": "TIMEOUT"}

    def test_entry_omits_none_context_fields(self, reset_logger):
        """Entry should not include context fields that are None."""
        lgr = reset_logger
        # No context set — all fields None
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(lgr, "_bs_enqueue") as mock_enqueue:
            lgr._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "started", None, None,
                "2025-01-01T12:00:00.000Z"
            )
            entry = mock_enqueue.call_args[0][0]
            assert "device_id" not in entry
            assert "workspace_id" not in entry
            assert "workspace_name" not in entry
            assert "tenant_id" not in entry

    def test_session_id_included_when_set(self, reset_logger):
        """Entry should include session_id when env var is set."""
        lgr = reset_logger
        lgr._session_id = "sess-abc"
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(lgr, "_bs_enqueue") as mock_enqueue:
            lgr._send_to_betterstack_logs(
                EventCode.APP_INIT_001, "started", None, None,
                "2025-01-01T12:00:00.000Z"
            )
            entry = mock_enqueue.call_args[0][0]
            assert entry["session_id"] == "sess-abc"


class TestBatching:
    """Verify buffer and flush behavior."""

    def test_entries_buffered(self, configured_logger):
        """Entries should be added to buffer."""
        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch.object(configured_logger, "_bs_flush"):
            # Enqueue without triggering flush
            for i in range(5):
                configured_logger._bs_enqueue({"msg": f"entry-{i}"})
            assert len(configured_logger._bs_buffer) == 5

    def test_flush_at_20_entries(self, configured_logger):
        """Buffer should auto-flush when 20 entries are reached."""
        with patch.object(configured_logger, "_bs_flush") as mock_flush:
            for i in range(20):
                configured_logger._bs_enqueue({"msg": f"entry-{i}"})
            mock_flush.assert_called_once()

    def test_timer_started_on_first_enqueue(self, configured_logger):
        """A 5-second flush timer should be started on first enqueue."""
        assert configured_logger._bs_flush_timer is None
        configured_logger._bs_enqueue({"msg": "first"})
        assert configured_logger._bs_flush_timer is not None
        assert configured_logger._bs_flush_timer.is_alive()
        # Cleanup
        configured_logger._bs_flush_timer.cancel()

    def test_flush_swaps_buffer(self, configured_logger):
        """Flush should swap buffer to empty and send old entries."""
        configured_logger._bs_buffer = [{"msg": "a"}, {"msg": "b"}]
        with patch.object(configured_logger, "_bs_send_batch") as mock_send:
            with patch("threading.Thread") as mock_thread_cls:
                mock_thread = MagicMock()
                mock_thread_cls.return_value = mock_thread
                configured_logger._bs_flush()
                assert configured_logger._bs_buffer == []
                mock_thread_cls.assert_called_once()
                mock_thread.start.assert_called_once()

    def test_flush_noop_when_empty(self, configured_logger):
        """Flush should be a no-op when buffer is empty."""
        with patch("threading.Thread") as mock_thread_cls:
            configured_logger._bs_flush()
            mock_thread_cls.assert_not_called()

    def test_flush_cancels_timer(self, configured_logger):
        """Flush should cancel any pending timer."""
        timer = threading.Timer(999, lambda: None)
        configured_logger._bs_flush_timer = timer
        configured_logger._bs_buffer = [{"msg": "x"}]
        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_cls.return_value = MagicMock()
            configured_logger._bs_flush()
        assert configured_logger._bs_flush_timer is None


class TestHTTPSending:
    """Verify the HTTP POST to Better Stack Logs."""

    def test_send_batch_posts_json(self, configured_logger):
        """Should POST JSON array to the configured host."""
        entries = [{"msg": "hello", "level": "info"}]

        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch("mitmproxy.addons.oximy.oximy_logger.urllib.request.build_opener") as mock_build:
            mock_opener = MagicMock()
            mock_build.return_value = mock_opener

            configured_logger._bs_send_batch(entries)

            mock_build.assert_called_once()
            mock_opener.open.assert_called_once()
            req = mock_opener.open.call_args[0][0]
            assert req.get_full_url() == "https://logs.example.com"
            assert req.get_method() == "POST"
            assert req.get_header("Authorization") == "Bearer tok-123"
            assert req.get_header("Content-type") == "application/json"
            payload = json.loads(req.data.decode("utf-8"))
            assert payload == entries

    def test_proxy_bypass(self, configured_logger):
        """Should use ProxyHandler({}) to bypass system proxy."""
        entries = [{"msg": "test"}]

        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch("mitmproxy.addons.oximy.oximy_logger.urllib.request.build_opener") as mock_build, \
             patch("mitmproxy.addons.oximy.oximy_logger.urllib.request.ProxyHandler") as mock_ph:
            mock_opener = MagicMock()
            mock_build.return_value = mock_opener

            configured_logger._bs_send_batch(entries)

            # ProxyHandler should be called with empty dict (bypass proxy)
            mock_ph.assert_called_once_with({})
            mock_build.assert_called_once_with(mock_ph.return_value)


class TestFailOpen:
    """Verify that exceptions in log sending never propagate."""

    def test_send_batch_swallows_exceptions(self, configured_logger):
        """HTTP errors should be silently caught."""
        entries = [{"msg": "test"}]

        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch("mitmproxy.addons.oximy.oximy_logger.urllib.request.build_opener") as mock_build:
            mock_opener = MagicMock()
            mock_opener.open.side_effect = Exception("connection refused")
            mock_build.return_value = mock_opener

            # Should not raise
            configured_logger._bs_send_batch(entries)

    def test_send_batch_swallows_url_errors(self, configured_logger):
        """URLError should be silently caught."""
        import urllib.error
        entries = [{"msg": "test"}]

        with patch.object(oximy_logger, "_BETTERSTACK_LOGS_TOKEN", "tok-123"), \
             patch.object(oximy_logger, "_BETTERSTACK_LOGS_HOST", "https://logs.example.com"), \
             patch("mitmproxy.addons.oximy.oximy_logger.urllib.request.build_opener") as mock_build:
            mock_opener = MagicMock()
            mock_opener.open.side_effect = urllib.error.URLError("timeout")
            mock_build.return_value = mock_opener

            configured_logger._bs_send_batch(entries)


class TestCloseFlush:
    """Verify that close() flushes remaining buffered logs."""

    def test_close_flushes_buffer(self, configured_logger):
        """close() should call _bs_flush() to send remaining entries."""
        configured_logger._bs_buffer = [{"msg": "remaining"}]
        with patch.object(configured_logger, "_bs_send_batch"):
            with patch("threading.Thread") as mock_thread_cls:
                mock_thread_cls.return_value = MagicMock()
                configured_logger.close()
                # Verify flush was called (buffer should be empty now)
                assert configured_logger._bs_buffer == []


class TestTenantIdInContext:
    """Verify tenant_id flows through set_context to JSONL and Better Stack."""

    def test_set_context_stores_tenant_id(self, reset_logger):
        lgr = reset_logger
        lgr.set_context(device_id="d", tenant_id="t-123")
        assert lgr._tenant_id == "t-123"

    def test_tenant_id_in_jsonl_ctx(self, reset_logger):
        """tenant_id should appear in the ctx dict of JSONL entries."""
        lgr = reset_logger
        lgr.set_context(device_id="d", tenant_id="t-123")
        with patch.object(lgr, "_ensure_file"), \
             patch.object(lgr, "_file", create=True) as mock_file:
            mock_file.write = MagicMock()
            mock_file.flush = MagicMock()
            lgr._write_jsonl(
                EventCode.APP_INIT_001, "test", None, None,
                "2025-01-01T00:00:00.000Z", 1
            )
            written = mock_file.write.call_args[0][0]
            entry = json.loads(written)
            assert entry["ctx"]["tenant_id"] == "t-123"

    def test_module_set_context_passes_tenant_id(self, reset_logger):
        """Module-level set_context should forward tenant_id."""
        oximy_logger.set_context(device_id="d", tenant_id="t-mod")
        assert oximy_logger._logger._tenant_id == "t-mod"
