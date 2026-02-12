from __future__ import annotations

import logging
import os
import platform
import sys
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False
_sentry_sdk: Any = None

# Oximy addon logger name prefixes — events from these loggers pass through.
# Includes both package-style (mitmproxy.addons.oximy.*) and standalone (addon, collector, etc.)
_OXIMY_LOGGER_PREFIXES = (
    "mitmproxy.addons.oximy",
    "addon",
    "collector",
    "normalize",
    "process",
    "oximy_logger",
    "sentry_service",
)

# Rate-limit state for auto-captured logging events: {(logger, message): (count, window_start)}
_auto_event_rate: dict[tuple[str, str], tuple[int, float]] = {}
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 60.0  # seconds


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


def _before_send(event: dict, hint: dict) -> dict | None:
    """Filter auto-captured logging events to only allow oximy addon logs.

    Events from explicit capture_message/capture_exception calls always pass through.
    Events auto-captured by LoggingIntegration are filtered by logger name and rate-limited.
    """
    log_record = hint.get("log_record")
    if log_record is None:
        # Explicit capture_message/capture_exception — always pass through
        return event

    # Filter by logger name — only allow oximy addon loggers
    logger_name = getattr(log_record, "name", "") or ""
    if not any(logger_name.startswith(prefix) for prefix in _OXIMY_LOGGER_PREFIXES):
        return None

    # Rate-limit: max _RATE_LIMIT_MAX events per logger+message per _RATE_LIMIT_WINDOW
    msg = getattr(log_record, "message", "") or getattr(log_record, "msg", "") or ""
    key = (logger_name, msg)
    now = time.monotonic()
    count, window_start = _auto_event_rate.get(key, (0, now))
    if now - window_start >= _RATE_LIMIT_WINDOW:
        # New window
        _auto_event_rate[key] = (1, now)
    elif count >= _RATE_LIMIT_MAX:
        return None
    else:
        _auto_event_rate[key] = (count + 1, window_start)

    # Tag auto-captured events for dashboard filtering
    tags = event.setdefault("tags", {})
    tags["capture_source"] = "logging_integration"

    return event


def initialize() -> bool:
    global _initialized
    with _lock:
        if _initialized:
            return True

        dsn = os.environ.get("SENTRY_DSN", "")
        if not dsn:
            logger.debug("No SENTRY_DSN env var — Sentry disabled for Python addon")
            return False

        sdk = _get_sdk()
        if not sdk:
            logger.debug("sentry-sdk not installed — Sentry disabled for Python addon")
            return False

        try:
            from sentry_sdk.integrations.logging import LoggingIntegration

            logging_integration = LoggingIntegration(
                level=logging.INFO,          # breadcrumbs from INFO+
                event_level=logging.ERROR,   # Sentry events from ERROR+ only
            )

            env = os.environ.get("OXIMY_ENV", "production")
            sdk.init(
                dsn=dsn,
                environment=env,
                default_integrations=False,
                auto_enabling_integrations=False,
                integrations=[logging_integration],
                before_send=_before_send,
                sample_rate=1.0,
                traces_sample_rate=0.0,
                send_default_pii=False,
                max_breadcrumbs=200,
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
                    scope.set_extras(extras)
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
                    scope.set_extras(extras)
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
