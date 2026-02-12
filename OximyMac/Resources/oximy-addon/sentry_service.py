"""Sentry wrapper for the Python addon — fail-open design.

Initializes from SENTRY_DSN environment variable (inherited from Swift parent process).
Thread-safe, lazy import of sentry_sdk. Works even if the package is not installed.
No automatic integrations (prevents interference with mitmproxy event loop).
"""
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
_sentry_sdk: Any = None  # lazy import


def _get_sdk():
    """Lazy-import sentry_sdk to avoid hard dependency."""
    global _sentry_sdk
    if _sentry_sdk is not None:
        return _sentry_sdk
    try:
        import sentry_sdk as sdk
        _sentry_sdk = sdk
        return sdk
    except ImportError:
        _sentry_sdk = False  # sentinel: import failed, don't retry
        return None


def initialize() -> bool:
    """Initialize Sentry from SENTRY_DSN env var. Returns True if initialized."""
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
            env = os.environ.get("OXIMY_ENV", "production")
            sdk.init(
                dsn=dsn,
                environment=env,
                # No automatic integrations — we only want manual events/breadcrumbs
                default_integrations=False,
                auto_enabling_integrations=False,
                # Send ALL events (not sampled)
                sample_rate=1.0,
                traces_sample_rate=0.0,  # no performance tracing
                # Don't send PII
                send_default_pii=False,
                # Max breadcrumbs
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
    """Set user context on the Sentry scope."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
    try:
        sdk.set_user({
            "id": device_id or "unknown",
            "username": workspace_name,
        })
    except Exception:
        pass


def set_tag(key: str, value: str) -> None:
    """Set a tag on the current Sentry scope."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
    try:
        sdk.set_tag(key, value)
    except Exception:
        pass


def set_initial_context() -> None:
    """Set initial device/platform context tags."""
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
    """Capture an exception to Sentry."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
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
    """Capture a message event to Sentry."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
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
    """Add a breadcrumb to the Sentry trail."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
    try:
        sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data,
        )
    except Exception:
        pass


def flush(timeout: float = 2.0) -> None:
    """Flush pending Sentry events."""
    if not _initialized:
        return
    sdk = _get_sdk()
    if not sdk:
        return
    try:
        sdk.flush(timeout=timeout)
    except Exception:
        pass
