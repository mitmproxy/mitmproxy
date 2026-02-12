"""Structured logger for the Python addon — dual output: console + JSONL file.

Usage:
    from mitmproxy.addons.oximy.oximy_logger import oximy_log, EventCode
    oximy_log(EventCode.CFG_FAIL_201, "HTTP error on config fetch", data={"status": 500})
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from mitmproxy.addons.oximy import sentry_service

logger = logging.getLogger(__name__)


# ─── Event Codes ────────────────────────────────────────────────────────

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ActionCategory(str, Enum):
    NONE = "none"
    MONITOR = "monitor"
    AUTO_RETRY = "auto_retry"
    SELF_HEALING = "self_healing"
    INVESTIGATE = "investigate"
    ALERT_OPS = "alert_ops"
    USER_ACTION = "user_action"


class EventCode(Enum):
    """Python addon event codes: (code_str, level, action)"""
    # Config
    CFG_FETCH_002 = ("CFG.FETCH.002", LogLevel.INFO, ActionCategory.NONE)
    CFG_FETCH_004 = ("CFG.FETCH.004", LogLevel.INFO, ActionCategory.NONE)
    CFG_FAIL_201 = ("CFG.FAIL.201", LogLevel.WARNING, ActionCategory.SELF_HEALING)
    CFG_FAIL_204 = ("CFG.FAIL.204", LogLevel.WARNING, ActionCategory.MONITOR)
    CFG_FAIL_205 = ("CFG.FAIL.205", LogLevel.ERROR, ActionCategory.AUTO_RETRY)
    CFG_CB_002 = ("CFG.CB.002", LogLevel.WARNING, ActionCategory.MONITOR)
    CFG_CB_003 = ("CFG.CB.003", LogLevel.INFO, ActionCategory.NONE)

    # Upload
    UPLOAD_STATE_101 = ("UPLOAD.STATE.101", LogLevel.INFO, ActionCategory.NONE)
    UPLOAD_FAIL_201 = ("UPLOAD.FAIL.201", LogLevel.ERROR, ActionCategory.ALERT_OPS)
    UPLOAD_FAIL_203 = ("UPLOAD.FAIL.203", LogLevel.WARNING, ActionCategory.AUTO_RETRY)
    UPLOAD_CB_002 = ("UPLOAD.CB.002", LogLevel.WARNING, ActionCategory.MONITOR)
    UPLOAD_CB_003 = ("UPLOAD.CB.003", LogLevel.INFO, ActionCategory.NONE)

    # State
    STATE_STATE_001 = ("STATE.STATE.001", LogLevel.INFO, ActionCategory.NONE)
    STATE_CMD_003 = ("STATE.CMD.003", LogLevel.WARNING, ActionCategory.USER_ACTION)

    # Trace
    TRACE_FAIL_201 = ("TRACE.FAIL.201", LogLevel.WARNING, ActionCategory.MONITOR)

    # Collector
    COLLECT_FAIL_202 = ("COLLECT.FAIL.202", LogLevel.WARNING, ActionCategory.AUTO_RETRY)
    COLLECT_FAIL_203 = ("COLLECT.FAIL.203", LogLevel.WARNING, ActionCategory.INVESTIGATE)

    # App lifecycle
    APP_INIT_001 = ("APP.INIT.001", LogLevel.INFO, ActionCategory.NONE)
    APP_STOP_001 = ("APP.STOP.001", LogLevel.INFO, ActionCategory.NONE)

    # System health
    SYS_HEALTH_001 = ("SYS.HEALTH.001", LogLevel.INFO, ActionCategory.NONE)

    @property
    def code(self) -> str:
        return self.value[0]

    @property
    def level(self) -> LogLevel:
        return self.value[1]

    @property
    def action(self) -> ActionCategory:
        return self.value[2]

    @property
    def service(self) -> str:
        return self.code.split(".")[0].lower()

    @property
    def operation(self) -> str:
        parts = self.code.split(".")
        return parts[1].lower() if len(parts) > 1 else "unknown"


# ─── Logger Singleton ───────────────────────────────────────────────────

class _OximyLogger:
    """Thread-safe structured logger with console + JSONL + Sentry output."""

    _MAX_FILE_SIZE = 50_000_000  # 50MB
    _MAX_ROTATED = 5

    def __init__(self) -> None:
        self._seq = 0
        self._lock = threading.Lock()
        self._file = None
        self._file_path: Path | None = None
        self._device_id: str | None = None
        self._workspace_id: str | None = None
        self._workspace_name: str | None = None
        self._session_id = os.environ.get("OXIMY_SESSION_ID", "")

    def set_context(self, *, device_id: str | None = None,
                    workspace_id: str | None = None,
                    workspace_name: str | None = None) -> None:
        self._device_id = device_id
        self._workspace_id = workspace_id
        self._workspace_name = workspace_name

    def emit(self, code: EventCode, msg: str, data: dict[str, Any] | None = None,
             err: dict[str, str] | None = None) -> None:
        """Emit a structured log event to console, JSONL, and Sentry."""
        with self._lock:
            self._seq += 1
            seq = self._seq

        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

        # Console output (human-readable)
        level_tags = {
            LogLevel.DEBUG: "[DEBUG]",
            LogLevel.INFO: "[INFO] ",
            LogLevel.WARNING: "[WARN] ",
            LogLevel.ERROR: "[ERROR]",
            LogLevel.FATAL: "[FATAL]",
        }
        level_tag = level_tags.get(code.level, "[INFO] ")

        data_str = ""
        if data:
            pairs = " ".join(f"{k}={v}" for k, v in sorted(data.items()))
            data_str = f" | {pairs}"

        log_fn = {
            LogLevel.DEBUG: logger.debug,
            LogLevel.INFO: logger.info,
            LogLevel.WARNING: logger.warning,
            LogLevel.ERROR: logger.error,
            LogLevel.FATAL: logger.critical,
        }.get(code.level, logger.info)

        log_fn(f"{level_tag} {code.code} {msg}{data_str}")

        # JSONL file output (AI-parseable)
        self._write_jsonl(code, msg, data, err, ts, seq)

        # Sentry output
        self._send_to_sentry(code, msg, data, err)

    def _write_jsonl(self, code: EventCode, msg: str, data: dict | None,
                     err: dict | None, ts: str, seq: int) -> None:
        entry: dict[str, Any] = {
            "v": 1,
            "seq": seq,
            "ts": ts,
            "code": code.code,
            "level": code.level.value,
            "svc": code.service,
            "op": code.operation,
            "msg": msg,
            "action": code.action.value,
        }

        ctx: dict[str, Any] = {"component": "python"}
        if self._session_id:
            ctx["session_id"] = self._session_id
        if self._device_id:
            ctx["device_id"] = self._device_id
        if self._workspace_id:
            ctx["workspace_id"] = self._workspace_id
        if self._workspace_name:
            ctx["workspace_name"] = self._workspace_name
        entry["ctx"] = ctx

        if data:
            entry["data"] = data
        if err:
            entry["err"] = err

        try:
            line = json.dumps(entry, default=str, sort_keys=True) + "\n"
            with self._lock:
                self._ensure_file()
                if self._file:
                    self._file.write(line)
                    self._file.flush()
                    self._rotate_if_needed()
        except Exception:
            pass  # fail-open: never crash on logging

    def _send_to_sentry(self, code: EventCode, msg: str, data: dict | None,
                        err: dict | None) -> None:
        if not sentry_service.is_initialized():
            return

        level_map = {
            LogLevel.DEBUG: "debug",
            LogLevel.INFO: "info",
            LogLevel.WARNING: "warning",
            LogLevel.ERROR: "error",
            LogLevel.FATAL: "fatal",
        }
        sentry_level = level_map.get(code.level, "info")

        # Always add breadcrumb for info+
        if code.level in (LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL):
            sentry_service.add_breadcrumb(
                category=code.service,
                message=f"[{code.code}] {msg}",
                level=sentry_level,
                data=data,
            )

        # Capture event for warning+
        if code.level in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL):
            tags = {
                "event_code": code.code,
                "service": code.service,
                "operation": code.operation,
                "action_category": code.action.value,
            }
            if err and "code" in err:
                tags["error_code"] = err["code"]

            sentry_service.capture_message(
                f"[{code.code}] {msg}",
                level=sentry_level,
                tags=tags,
                extras=data,
            )

    def _ensure_file(self) -> None:
        if self._file is not None:
            return
        try:
            logs_dir = Path.home() / ".oximy" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            self._file_path = logs_dir / "sensor.jsonl"
            self._file = open(self._file_path, "a", encoding="utf-8")
        except Exception:
            self._file = None

    def _rotate_if_needed(self) -> None:
        if not self._file_path or not self._file_path.exists():
            return
        try:
            if self._file_path.stat().st_size < self._MAX_FILE_SIZE:
                return
        except OSError:
            return

        # Close current file
        if self._file:
            self._file.close()
            self._file = None

        logs_dir = self._file_path.parent

        # Shift rotated files
        for i in range(self._MAX_ROTATED - 1, 0, -1):
            src = logs_dir / f"sensor.{i}.jsonl"
            dst = logs_dir / f"sensor.{i + 1}.jsonl"
            try:
                if dst.exists():
                    dst.unlink()
                if src.exists():
                    src.rename(dst)
            except OSError:
                pass

        # Current → sensor.1.jsonl
        try:
            rotated = logs_dir / "sensor.1.jsonl"
            if rotated.exists():
                rotated.unlink()
            self._file_path.rename(rotated)
        except OSError:
            pass

        # Reopen
        self._ensure_file()

    def close(self) -> None:
        with self._lock:
            if self._file:
                try:
                    self._file.flush()
                    self._file.close()
                except Exception:
                    pass
                self._file = None


# Module-level singleton
_logger = _OximyLogger()


def oximy_log(code: EventCode, msg: str, data: dict[str, Any] | None = None,
              err: dict[str, str] | None = None) -> None:
    """Emit a structured log event. Module-level convenience function."""
    _logger.emit(code, msg, data, err)


def set_context(*, device_id: str | None = None,
                workspace_id: str | None = None,
                workspace_name: str | None = None) -> None:
    """Update logger context (device/workspace info)."""
    _logger.set_context(device_id=device_id, workspace_id=workspace_id,
                        workspace_name=workspace_name)


def close() -> None:
    """Close the JSONL file handle."""
    _logger.close()
