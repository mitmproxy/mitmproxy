from __future__ import annotations

import logging
import os
import platform
import sys
import threading
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False
_sentry_sdk: Any = None


def _get_sdk():
    global _sentry_sdk
    if _sentry_sdk is not None:
        return _sentry_sdk
    try:
        import sentry_sdk as sdk
        _sentry_sdk = sdk
        return sdk
    except ImportError:
        return None


def _sdk_or_none():
    """Return the SDK if initialized and available, else None."""
    if not _initialized:
        return None
    return _get_sdk()


def initialize() -> bool:
    global _initialized
    with _lock:
        if _initialized:
            return True

        dsn = os.environ.get("BETTERSTACK_ERRORS_DSN") or os.environ.get("SENTRY_DSN", "")
        if not dsn:
            logger.debug("No BETTERSTACK_ERRORS_DSN or SENTRY_DSN env var — error tracking disabled for Python addon")
            return False

        sdk = _get_sdk()
        if not sdk:
            logger.debug("sentry-sdk not installed — Sentry disabled for Python addon")
            return False

        try:
            from sentry_sdk.integrations.logging import LoggingIntegration

            logging_integration = LoggingIntegration(
                level=logging.INFO,          # breadcrumbs from INFO+
                event_level=None,            # no auto-capture — explicit capture_message() only
            )

            # StdlibIntegration auto-captures urllib HTTP calls (ingestion uploads,
            # config fetches) as HTTP breadcrumbs — matches Swift SDK's HTTP tracking
            integrations = [logging_integration]
            try:
                from sentry_sdk.integrations.stdlib import StdlibIntegration
                integrations.append(StdlibIntegration())
            except (ImportError, Exception):
                logger.debug("StdlibIntegration not available — urllib HTTP breadcrumbs disabled")

            env = os.environ.get("OXIMY_ENV", "production")
            sdk.init(
                dsn=dsn,
                environment=env,
                integrations=integrations,
                sample_rate=1.0,
                traces_sample_rate=0.0,
                send_default_pii=False,
                max_breadcrumbs=200,
                # Bypass the Oximy proxy for Sentry's own HTTP calls —
                # the addon runs inside mitmproxy, so system proxy points
                # back to ourselves which breaks Sentry event delivery
                http_proxy="",
                https_proxy="",
            )

            _initialized = True
            logger.debug("Sentry initialized for Python addon")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}")
            return False


def is_initialized() -> bool:
    return _initialized


def set_user(device_id: str | None = None, workspace_id: str | None = None,
             workspace_name: str | None = None) -> None:
    if sdk := _sdk_or_none():
        try:
            sdk.set_user({
                "id": device_id or "unknown",
                "username": workspace_name,
            })
        except Exception:
            pass


def set_tag(key: str, value: str) -> None:
    if sdk := _sdk_or_none():
        try:
            sdk.set_tag(key, value)
        except Exception:
            pass


def set_initial_context() -> None:
    set_tag("component", "python")
    set_tag("platform", sys.platform)
    set_tag("python_version", platform.python_version())
    set_tag("architecture", platform.machine())

    session_id = os.environ.get("OXIMY_SESSION_ID", "")
    if session_id:
        set_tag("session_id", session_id)


def capture_exception(exc: BaseException | None = None,
                      tags: dict[str, str] | None = None,
                      extras: dict[str, Any] | None = None) -> None:
    if sdk := _sdk_or_none():
        try:
            with sdk.push_scope() as scope:
                if tags:
                    for k, v in tags.items():
                        scope.set_tag(k, v)
                if extras:
                    for k, v in extras.items():
                        scope.set_extra(k, v)
                sdk.capture_exception(exc)
        except Exception:
            pass


def capture_message(message: str, level: str = "info",
                    tags: dict[str, str] | None = None,
                    extras: dict[str, Any] | None = None) -> None:
    if sdk := _sdk_or_none():
        try:
            with sdk.push_scope() as scope:
                scope.set_level(level)
                if tags:
                    for k, v in tags.items():
                        scope.set_tag(k, v)
                if extras:
                    for k, v in extras.items():
                        scope.set_extra(k, v)
                sdk.capture_message(message)
        except Exception:
            pass


def add_breadcrumb(category: str, message: str, level: str = "info",
                   data: dict[str, Any] | None = None) -> None:
    if sdk := _sdk_or_none():
        try:
            sdk.add_breadcrumb(
                category=category,
                message=message,
                level=level,
                data=data,
            )
        except Exception:
            pass


def flush() -> None:
    if sdk := _sdk_or_none():
        try:
            sdk.flush(timeout=2)
        except Exception:
            pass
