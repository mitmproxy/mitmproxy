from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from mitmproxy.addons.oximy import sentry_service
except ImportError:
    try:
        import sentry_service  # type: ignore[import]
    except ImportError:
        sentry_service = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ─── Event Codes ────────────────────────────────────────────────────────

class EventCode(Enum):
    # (code_str, level, action)
    # Config
    CFG_FAIL_201 = ("CFG.FAIL.201", "warning", "self_healing")
    CFG_FAIL_205 = ("CFG.FAIL.205", "error", "auto_retry")
    CFG_CB_002 = ("CFG.CB.002", "warning", "monitor")
    CFG_CB_003 = ("CFG.CB.003", "info", "none")

    # Upload
    UPLOAD_STATE_101 = ("UPLOAD.STATE.101", "info", "none")
    UPLOAD_FAIL_201 = ("UPLOAD.FAIL.201", "error", "alert_ops")
    UPLOAD_FAIL_203 = ("UPLOAD.FAIL.203", "warning", "auto_retry")
    UPLOAD_CB_002 = ("UPLOAD.CB.002", "warning", "monitor")
    UPLOAD_CB_003 = ("UPLOAD.CB.003", "info", "none")

    # State
    STATE_STATE_001 = ("STATE.STATE.001", "info", "none")
    STATE_CMD_003 = ("STATE.CMD.003", "warning", "user_action")

    # Trace
    TRACE_CAPTURE_001 = ("TRACE.CAPTURE.001", "info", "none")
    TRACE_WRITE_001 = ("TRACE.WRITE.001", "info", "none")
    TRACE_FAIL_201 = ("TRACE.FAIL.201", "warning", "monitor")

    # Collector
    COLLECT_FAIL_202 = ("COLLECT.FAIL.202", "warning", "auto_retry")
    COLLECT_FAIL_203 = ("COLLECT.FAIL.203", "warning", "investigate")

    # App lifecycle
    APP_INIT_001 = ("APP.INIT.001", "info", "none")
    APP_STOP_001 = ("APP.STOP.001", "info", "none")


# ─── Module-level constants ─────────────────────────────────────────────

_LEVEL_TAGS = {
    "debug": "[DEBUG]",
    "info": "[INFO] ",
    "warning": "[WARN] ",
    "error": "[ERROR]",
    "fatal": "[FATAL]",
}

_LOG_FNS = {
    "debug": logger.debug,
    "info": logger.info,
    "warning": logger.warning,
    "error": logger.error,
    "fatal": logger.critical,
}

_SENTRY_LEVELS = {"debug", "info", "warning", "error", "fatal"}
_INFO_PLUS = {"info", "warning", "error", "fatal"}

_BETTERSTACK_LOGS_TOKEN = os.environ.get("BETTERSTACK_LOGS_TOKEN", "")
_BETTERSTACK_LOGS_HOST = os.environ.get("BETTERSTACK_LOGS_HOST", "")


# ─── Logger Singleton ───────────────────────────────────────────────────

class _OximyLogger:
    _MAX_FILE_SIZE = 50_000_000  # 50MB
    _MAX_ROTATED = 5

    _MAX_SENTRY_EVENTS_PER_CODE = 10
    _SENTRY_RATE_WINDOW_S = 60

    def __init__(self) -> None:
        self._seq = 0
        self._lock = threading.Lock()
        self._file = None
        self._file_path: Path | None = None
        self._device_id: str | None = None
        self._workspace_id: str | None = None
        self._workspace_name: str | None = None
        self._tenant_id: str | None = None
        self._session_id = os.environ.get("OXIMY_SESSION_ID", "")
        self._sentry_counts: dict[str, tuple[int, float]] = {}
        # Better Stack Logs batching
        self._bs_buffer: list[dict] = []
        self._bs_flush_timer: threading.Timer | None = None
        self._bs_lock = threading.Lock()

    def set_context(self, *, device_id: str | None = None,
                    workspace_id: str | None = None,
                    workspace_name: str | None = None,
                    tenant_id: str | None = None) -> None:
        self._device_id = device_id
        self._workspace_id = workspace_id
        self._workspace_name = workspace_name
        self._tenant_id = tenant_id

    def emit(self, code: EventCode, msg: str, data: dict[str, Any] | None = None,
             err: dict[str, str] | None = None) -> None:
        with self._lock:
            self._seq += 1
            seq = self._seq

        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

        level = code.value[1]

        # Console output
        level_tag = _LEVEL_TAGS.get(level, "[INFO] ")

        data_str = ""
        if data:
            pairs = " ".join(f"{k}={v}" for k, v in sorted(data.items()))
            data_str = f" | {pairs}"

        log_fn = _LOG_FNS.get(level, logger.info)
        log_fn(f"{level_tag} {code.value[0]} {msg}{data_str}")

        # JSONL file output
        self._write_jsonl(code, msg, data, err, ts, seq)

        # Sentry output
        self._send_to_sentry(code, msg, data, err)

        # Better Stack Logs output
        self._send_to_betterstack_logs(code, msg, data, err, ts)

    def _write_jsonl(self, code: EventCode, msg: str, data: dict | None,
                     err: dict | None, ts: str, seq: int) -> None:
        code_str, level, action = code.value
        parts = code_str.split(".")

        entry: dict[str, Any] = {
            "v": 1,
            "seq": seq,
            "ts": ts,
            "code": code_str,
            "level": level,
            "svc": parts[0].lower(),
            "op": parts[1].lower() if len(parts) > 1 else "unknown",
            "msg": msg,
            "action": action,
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
        if self._tenant_id:
            ctx["tenant_id"] = self._tenant_id
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

        code_str, level, action = code.value
        parts = code_str.split(".")
        service = parts[0].lower()
        operation = parts[1].lower() if len(parts) > 1 else "unknown"

        if level not in _INFO_PLUS:
            return

        # Always add breadcrumb for info+
        sentry_service.add_breadcrumb(
            category=service,
            message=f"[{code_str}] {msg}",
            level=level,
            data=data,
        )

        # Capture event (rate-limited per event code)
        if not self._should_send_sentry_event(code_str):
            return

        tags = {
            "event_code": code_str,
            "service": service,
            "operation": operation,
            "action_category": action,
        }
        if err and "code" in err:
            tags["error_code"] = err["code"]

        sentry_service.capture_message(
            f"[{code_str}] {msg}",
            level=level,
            tags=tags,
            extras=data,
        )

    def _should_send_sentry_event(self, code: str) -> bool:
        """Rate-limit Sentry events: max N per event code per minute window."""
        now = time.monotonic()
        entry = self._sentry_counts.get(code)
        if entry is not None:
            count, window_start = entry
            if now - window_start > self._SENTRY_RATE_WINDOW_S:
                self._sentry_counts[code] = (1, now)
                return True
            if count >= self._MAX_SENTRY_EVENTS_PER_CODE:
                return False
            self._sentry_counts[code] = (count + 1, window_start)
            return True
        self._sentry_counts[code] = (1, now)
        return True

    def _send_to_betterstack_logs(self, code: EventCode, msg: str, data: dict | None,
                                   err: dict | None, ts: str) -> None:
        if not _BETTERSTACK_LOGS_TOKEN or not _BETTERSTACK_LOGS_HOST:
            return

        level = code.value[1]
        if level not in _INFO_PLUS:
            return

        code_str, _, action = code.value
        parts = code_str.split(".")

        entry: dict[str, Any] = {
            "dt": ts,
            "level": level,
            "code": code_str,
            "svc": parts[0].lower(),
            "op": parts[1].lower() if len(parts) > 1 else "unknown",
            "msg": msg,
            "action": action,
            "component": "python",
        }
        if self._session_id:
            entry["session_id"] = self._session_id
        if self._device_id:
            entry["device_id"] = self._device_id
        if self._workspace_id:
            entry["workspace_id"] = self._workspace_id
        if self._workspace_name:
            entry["workspace_name"] = self._workspace_name
        if self._tenant_id:
            entry["tenant_id"] = self._tenant_id
        if data:
            entry["data"] = data
        if err:
            entry["err"] = err

        self._bs_enqueue(entry)

    def _bs_enqueue(self, entry: dict) -> None:
        with self._bs_lock:
            self._bs_buffer.append(entry)
            if len(self._bs_buffer) >= 20:
                self._bs_flush()
                return
            if self._bs_flush_timer is None or not self._bs_flush_timer.is_alive():
                self._bs_flush_timer = threading.Timer(5.0, self._bs_flush)
                self._bs_flush_timer.daemon = True
                self._bs_flush_timer.start()

    def _bs_flush(self) -> None:
        with self._bs_lock:
            entries = self._bs_buffer
            self._bs_buffer = []
            if self._bs_flush_timer is not None:
                self._bs_flush_timer.cancel()
                self._bs_flush_timer = None
        if not entries:
            return
        t = threading.Thread(target=self._bs_send_batch, args=(entries,), daemon=True)
        t.start()

    def _bs_send_batch(self, entries: list[dict]) -> None:
        try:
            payload = json.dumps(entries, default=str).encode("utf-8")
            req = urllib.request.Request(
                _BETTERSTACK_LOGS_HOST,
                data=payload,
                headers={
                    "Authorization": f"Bearer {_BETTERSTACK_LOGS_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            # Bypass proxy — the addon runs inside mitmproxy so system proxy
            # points back to ourselves which would cause a loop
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            opener.open(req, timeout=10)
        except Exception:
            pass  # fail-open: never crash on log sending

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

        if self._file:
            self._file.close()
            self._file = None

        logs_dir = self._file_path.parent

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

        try:
            rotated = logs_dir / "sensor.1.jsonl"
            if rotated.exists():
                rotated.unlink()
            self._file_path.rename(rotated)
        except OSError:
            pass

        self._ensure_file()

    def close(self) -> None:
        self._bs_flush()
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
    _logger.emit(code, msg, data, err)


def set_context(*, device_id: str | None = None,
                workspace_id: str | None = None,
                workspace_name: str | None = None,
                tenant_id: str | None = None) -> None:
    _logger.set_context(device_id=device_id, workspace_id=workspace_id,
                        workspace_name=workspace_name, tenant_id=tenant_id)


def close() -> None:
    _logger.close()
