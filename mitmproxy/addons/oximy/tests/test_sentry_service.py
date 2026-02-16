"""Unit tests for sentry_service.py — Sentry wrapper (fail-open design).

Tests verify the fail-open behavior: all functions must be no-ops
when Sentry is not initialized (no SENTRY_DSN, no sentry_sdk package).
"""

from __future__ import annotations

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from mitmproxy.addons.oximy import sentry_service


@pytest.fixture(autouse=True)
def reset_sentry_state():
    """Reset sentry_service module state between tests."""
    sentry_service._initialized = False
    sentry_service._sentry_sdk = None
    yield
    sentry_service._initialized = False
    sentry_service._sentry_sdk = None


@pytest.fixture()
def mock_sentry_modules():
    """Inject mock sentry_sdk module hierarchy into sys.modules.

    Required for tests that call initialize() since sentry_sdk may not be installed.
    The LoggingIntegration mock is returned so tests can assert on it.
    """
    mock_logging_integration_cls = MagicMock()
    mock_logging_mod = MagicMock()
    mock_logging_mod.LoggingIntegration = mock_logging_integration_cls
    mock_stdlib_mod = MagicMock()
    mock_integrations = MagicMock()
    mock_integrations.logging = mock_logging_mod
    mock_integrations.stdlib = mock_stdlib_mod
    mock_sentry = MagicMock()
    mock_sentry.integrations = mock_integrations
    mock_sentry.integrations.logging = mock_logging_mod
    mock_sentry.integrations.stdlib = mock_stdlib_mod

    modules = {
        "sentry_sdk": mock_sentry,
        "sentry_sdk.integrations": mock_integrations,
        "sentry_sdk.integrations.logging": mock_logging_mod,
        "sentry_sdk.integrations.stdlib": mock_stdlib_mod,
    }
    with patch.dict(sys.modules, modules):
        yield mock_logging_integration_cls


class TestInitialize:
    def test_no_dsn_returns_false(self):
        """Should return False when neither BETTERSTACK_ERRORS_DSN nor SENTRY_DSN is set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTRY_DSN", None)
            os.environ.pop("BETTERSTACK_ERRORS_DSN", None)
            assert sentry_service.initialize() is False
            assert sentry_service.is_initialized() is False

    def test_empty_dsn_returns_false(self):
        """Should return False when SENTRY_DSN is empty and BETTERSTACK_ERRORS_DSN not set."""
        with patch.dict(os.environ, {"SENTRY_DSN": ""}, clear=True):
            assert sentry_service.initialize() is False

    def test_betterstack_errors_dsn_takes_priority(self, mock_sentry_modules):
        """BETTERSTACK_ERRORS_DSN should take priority over SENTRY_DSN."""
        mock_sdk = MagicMock()
        env = {
            "BETTERSTACK_ERRORS_DSN": "https://bs-key@errors.betterstack.com/1",
            "SENTRY_DSN": "https://sentry-key@sentry.io/123",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is True
                call_kwargs = mock_sdk.init.call_args[1]
                assert call_kwargs["dsn"] == "https://bs-key@errors.betterstack.com/1"

    def test_sentry_dsn_fallback(self, mock_sentry_modules):
        """SENTRY_DSN should be used when BETTERSTACK_ERRORS_DSN is not set."""
        mock_sdk = MagicMock()
        with patch.dict(os.environ, {"SENTRY_DSN": "https://sentry-key@sentry.io/123"}, clear=True):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is True
                call_kwargs = mock_sdk.init.call_args[1]
                assert call_kwargs["dsn"] == "https://sentry-key@sentry.io/123"

    def test_sdk_not_installed_returns_false(self):
        """Should return False when sentry_sdk is not importable."""
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=None):
                assert sentry_service.initialize() is False

    def test_sdk_init_succeeds(self, mock_sentry_modules):
        """Should return True when SDK initializes successfully."""
        mock_sdk = MagicMock()
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is True
                assert sentry_service.is_initialized() is True
                mock_sdk.init.assert_called_once()

    def test_sdk_init_exception_returns_false(self, mock_sentry_modules):
        """Should return False when SDK init raises."""
        mock_sdk = MagicMock()
        mock_sdk.init.side_effect = Exception("init failed")
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is False
                assert sentry_service.is_initialized() is False

    def test_idempotent_init(self, mock_sentry_modules):
        """Should return True on second call without re-initializing."""
        mock_sdk = MagicMock()
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is True
                assert sentry_service.initialize() is True
                # init only called once
                assert mock_sdk.init.call_count == 1


class TestFailOpen:
    """All public functions must be safe to call when not initialized."""

    def test_set_user_noop(self):
        sentry_service.set_user(device_id="test", workspace_id="ws")

    def test_set_tag_noop(self):
        sentry_service.set_tag("key", "value")

    def test_set_initial_context_noop(self):
        sentry_service.set_initial_context()

    def test_capture_exception_noop(self):
        sentry_service.capture_exception(Exception("test"))

    def test_capture_message_noop(self):
        sentry_service.capture_message("test message", level="error")

    def test_add_breadcrumb_noop(self):
        sentry_service.add_breadcrumb(
            category="test", message="test", level="info"
        )

    def test_flush_noop(self):
        sentry_service.flush()


class TestSetUser:
    def test_set_user_calls_sdk(self):
        mock_sdk = MagicMock()
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.set_user(
            device_id="dev-123", workspace_name="Acme"
        )
        mock_sdk.set_user.assert_called_once_with({
            "id": "dev-123",
            "username": "Acme",
        })

    def test_set_user_default_id(self):
        mock_sdk = MagicMock()
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.set_user()
        mock_sdk.set_user.assert_called_once_with({
            "id": "unknown",
            "username": None,
        })


class TestSetTag:
    def test_set_tag_calls_sdk(self):
        mock_sdk = MagicMock()
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.set_tag("component", "python")
        mock_sdk.set_tag.assert_called_once_with("component", "python")


class TestCaptureMessage:
    def test_capture_message_with_tags_and_extras(self):
        mock_sdk = MagicMock()
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.capture_message(
            "test message",
            level="warning",
            tags={"event_code": "CFG.FAIL.201"},
            extras={"status": 500},
        )

        mock_scope.set_level.assert_called_once_with("warning")
        mock_scope.set_tag.assert_called_once_with("event_code", "CFG.FAIL.201")
        mock_scope.set_extra.assert_called_once_with("status", 500)
        mock_sdk.capture_message.assert_called_once_with("test message")


class TestCaptureException:
    def test_capture_exception_calls_sdk(self):
        mock_sdk = MagicMock()
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        exc = ValueError("test error")
        sentry_service.capture_exception(exc, tags={"service": "upload"})

        mock_scope.set_tag.assert_called_once_with("service", "upload")
        mock_sdk.capture_exception.assert_called_once_with(exc)


class TestAddBreadcrumb:
    def test_add_breadcrumb_calls_sdk(self):
        mock_sdk = MagicMock()
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.add_breadcrumb(
            category="config",
            message="Config loaded",
            level="info",
            data={"domains": 42},
        )
        mock_sdk.add_breadcrumb.assert_called_once_with(
            category="config",
            message="Config loaded",
            level="info",
            data={"domains": 42},
        )


class TestFlush:
    def test_flush_calls_sdk(self):
        mock_sdk = MagicMock()
        sentry_service._initialized = True
        sentry_service._sentry_sdk = mock_sdk

        sentry_service.flush()
        mock_sdk.flush.assert_called_once_with(timeout=2)


class TestGetSdk:
    def test_lazy_import_returns_none_on_failure(self):
        sentry_service._sentry_sdk = None
        with patch("builtins.__import__", side_effect=ImportError):
            result = sentry_service._get_sdk()
        assert result is None

    def test_caches_sdk_after_successful_import(self):
        sentry_service._sentry_sdk = None
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sdk}):
            result = sentry_service._get_sdk()
        assert result is mock_sdk
        assert sentry_service._sentry_sdk is mock_sdk


class TestLoggingIntegration:
    """Verify sdk.init() receives LoggingIntegration with breadcrumbs only."""

    def test_init_passes_integrations_no_before_send(self, mock_sentry_modules):
        """sdk.init() should receive integrations list and no before_send callback."""
        mock_li_cls = mock_sentry_modules
        mock_li_instance = MagicMock()
        mock_li_cls.return_value = mock_li_instance

        mock_sdk = MagicMock()
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                assert sentry_service.initialize() is True

                call_kwargs = mock_sdk.init.call_args[1]
                assert "integrations" in call_kwargs
                assert mock_li_instance in call_kwargs["integrations"]
                assert "before_send" not in call_kwargs

    def test_init_configures_logging_integration_breadcrumbs_only(self, mock_sentry_modules):
        """LoggingIntegration should use INFO for breadcrumbs, None for events."""
        mock_li_cls = mock_sentry_modules

        mock_sdk = MagicMock()
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch.object(sentry_service, "_get_sdk", return_value=mock_sdk):
                sentry_service.initialize()
                mock_li_cls.assert_called_once_with(
                    level=logging.INFO,
                    event_level=None,
                )
