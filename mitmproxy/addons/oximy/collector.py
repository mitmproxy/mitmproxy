"""
LocalDataCollector — reads local AI tool session files and uploads to API.

Dumb pipe: reads files, wraps raw JSON in envelope, POSTs to API.
All parsing/normalization happens server-side.
"""

from __future__ import annotations

import fnmatch
import glob as glob_module
import gzip
import json
import logging
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from watchfiles import watch, Change
    HAS_WATCHFILES = True
except ImportError:
    HAS_WATCHFILES = False

try:
    from mitmproxy.addons.oximy import sentry_service
    from mitmproxy.addons.oximy.oximy_logger import oximy_log, EventCode
except ImportError:
    try:
        import sentry_service  # type: ignore[import]
        from oximy_logger import oximy_log, EventCode  # type: ignore[import]
    except ImportError:
        sentry_service = None  # type: ignore[assignment]
        oximy_log = None  # type: ignore[assignment]
        EventCode = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
OXIMY_DIR = Path(os.environ.get("OXIMY_HOME", "~/.oximy")).expanduser()
SCAN_STATE_FILE = OXIMY_DIR / "local-scan-state.json"
OXIMY_TOKEN_FILE = OXIMY_DIR / "device-token"

# API base URL resolution — same logic as addon.py to avoid circular import.
# Priority: OXIMY_API_URL env > ~/.oximy/dev.json API_URL > hardcoded default
_DEFAULT_API_BASE = "https://api.oximy.com/api/v1"

def _resolve_collector_api_base() -> str:
    env_url = os.environ.get("OXIMY_API_URL")
    if env_url:
        return env_url.rstrip("/")
    try:
        dev_config = OXIMY_DIR / "dev.json"
        if dev_config.exists():
            with open(dev_config, encoding="utf-8") as f:
                cfg = json.load(f)
            api_url = cfg.get("API_URL")
            if api_url and isinstance(api_url, str):
                return api_url.rstrip("/")
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return _DEFAULT_API_BASE

_collector_api_base = _resolve_collector_api_base()

DEFAULT_LOCAL_INGEST_URL = f"{_collector_api_base}/ingest/local-sessions"
DEFAULT_MAX_EVENT_SIZE = 1_048_576  # 1 MB
DEFAULT_MAX_EVENTS_PER_BATCH = 200
DEFAULT_MAX_BATCH_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB compressed
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_POLL_INTERVAL = 3  # seconds (fallback)
DEFAULT_BACKFILL_MAX_AGE_DAYS = 7

def generate_event_id() -> str:
    """Generate UUID v7 (time-sortable)."""
    ts = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    uuid_int = (ts << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    h = f"{uuid_int:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _compile_redact_patterns(patterns: list[str]) -> list[re.Pattern]:
    """Pre-compile redaction regex patterns for performance."""
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error as e:
            logger.warning(f"Invalid redact pattern '{p}': {e}")
    return compiled


def redact_sensitive(raw_line: str, compiled_patterns: list[re.Pattern]) -> str:
    """Apply regex-based redaction to raw JSON string before parsing."""
    for pattern in compiled_patterns:
        raw_line = pattern.sub("[REDACTED]", raw_line)
    return raw_line


def _should_skip_file(filename: str, skip_patterns: list[str]) -> bool:
    """Check if file matches any skip pattern (e.g., *auth*, *.pem)."""
    for pattern in skip_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def _resolve_query_order(queries: list[dict]) -> list[dict]:
    """Topological sort of SQLite queries based on 'depends_on' field.

    Returns queries in dependency-safe execution order.
    Raises ValueError if circular dependency or unknown target detected.
    """
    by_type = {q["file_type"]: q for q in queries}
    order: list[dict] = []
    visited: set[str] = set()
    in_stack: set[str] = set()

    def visit(ft: str) -> None:
        if ft in in_stack:
            raise ValueError(f"Circular dependency in SQLite queries: {ft}")
        if ft in visited:
            return
        in_stack.add(ft)
        dep = by_type[ft].get("depends_on")
        if dep:
            if dep not in by_type:
                raise ValueError(f"Unknown depends_on target: {dep}")
            visit(dep)
        in_stack.discard(ft)
        visited.add(ft)
        order.append(by_type[ft])

    for q in queries:
        visit(q["file_type"])
    return order


def _extract_metadata_from_path(filepath: str, source_name: str) -> dict:
    """Extract envelope metadata from file path.

    Returns dict with: source_file, project_key (optional), session_id (optional)
    """
    home = str(Path.home())
    if filepath.startswith(home):
        source_file = "~" + filepath[len(home):]
    else:
        source_file = filepath

    result: dict[str, Any] = {"source_file": source_file}

    parts = Path(filepath).parts

    if source_name == "claude_code":
        try:
            proj_idx = parts.index("projects")
            if proj_idx + 1 < len(parts):
                result["project_key"] = parts[proj_idx + 1]
        except ValueError:
            pass
        stem = Path(filepath).stem
        if stem not in ("sessions-index", "history", "stats-cache"):
            result["session_id"] = stem

    elif source_name == "cursor":
        # ~/.cursor/projects/<project_key>/agent-transcripts/<filename>.json
        try:
            proj_idx = parts.index("projects")
            if proj_idx + 1 < len(parts):
                result["project_key"] = parts[proj_idx + 1]
        except ValueError:
            pass

    elif source_name == "codex":
        # ~/.codex/sessions/<session_id>.jsonl
        try:
            sess_idx = parts.index("sessions")
            if sess_idx + 1 < len(parts):
                stem = Path(parts[sess_idx + 1]).stem
                if stem != "sessions":
                    result["session_id"] = stem
        except ValueError:
            pass

    elif source_name == "openclaw":
        # ~/.openclaw/agents/main/sessions/<session_id>.jsonl
        try:
            sess_idx = parts.index("sessions")
            if sess_idx + 1 < len(parts):
                stem = Path(parts[sess_idx + 1]).stem
                if stem != "sessions":
                    result["session_id"] = stem
        except ValueError:
            pass

    return result


# ---------------------------------------------------------------------------
# ScanState — persistent byte offsets / mtimes
# ---------------------------------------------------------------------------

class ScanState:
    """Persists per-file scan offsets/mtimes to disk."""

    def __init__(self, state_file: Path | None = None):
        self._state_file = state_file or SCAN_STATE_FILE
        self._data: dict = {"version": 1, "sources": {}}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self._state_file.exists():
            try:
                with open(self._state_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                if loaded.get("version") == 1:
                    self._data = loaded
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load scan state: {e}")

    def save(self) -> None:
        with self._lock:
            try:
                self._state_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._state_file.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
                tmp.replace(self._state_file)
            except IOError as e:
                logger.warning(f"Failed to save scan state: {e}")

    def get_file_state(self, source: str, filepath: str) -> dict:
        with self._lock:
            return (
                self._data
                .get("sources", {})
                .get(source, {})
                .get("files", {})
                .get(filepath, {})
            )

    def set_file_state(self, source: str, filepath: str, offset: int, mtime: float) -> None:
        with self._lock:
            sources = self._data.setdefault("sources", {})
            src = sources.setdefault(source, {})
            files = src.setdefault("files", {})
            files[filepath] = {"offset": offset, "mtime": mtime}

    def get_sqlite_state(self, source: str, db_key: str) -> dict:
        """Get state for a SQLite database.

        db_key is the basename of the database file (e.g., 'state.vscdb').
        Returns dict with 'mtime' and 'incremental' keys, or empty dict.
        """
        with self._lock:
            return (
                self._data
                .get("sources", {})
                .get(source, {})
                .get("sqlite", {})
                .get(db_key, {})
            )

    def set_sqlite_mtime(self, source: str, db_key: str, mtime: float) -> None:
        """Update mtime for a SQLite database."""
        with self._lock:
            sources = self._data.setdefault("sources", {})
            src = sources.setdefault(source, {})
            sqlite = src.setdefault("sqlite", {})
            db = sqlite.setdefault(db_key, {})
            db["mtime"] = mtime

    def set_sqlite_incremental(
        self, source: str, db_key: str, file_type: str, last_value: Any
    ) -> None:
        """Update incremental tracking value for a specific query/file_type."""
        with self._lock:
            sources = self._data.setdefault("sources", {})
            src = sources.setdefault(source, {})
            sqlite = src.setdefault("sqlite", {})
            db = sqlite.setdefault(db_key, {})
            incremental = db.setdefault("incremental", {})
            incremental[file_type] = {"last_value": last_value}

    def is_first_run(self) -> bool:
        """True if no state file existed on disk when we loaded."""
        with self._lock:
            return not any(
                src.get("files") or src.get("sqlite")
                for src in self._data.get("sources", {}).values()
            )


# ---------------------------------------------------------------------------
# LocalDataCollector
# ---------------------------------------------------------------------------

class LocalDataCollector:
    """Polls local AI tool session files and uploads to API.

    Lifecycle:
        collector = LocalDataCollector(config, device_id)
        collector.start()
        collector.update_config(config)
        collector.stop()
    """

    def __init__(self, config: dict, device_id: str | None = None,
                 api_base_url: str | None = None):
        self._config = config
        self._device_id = device_id
        self._api_base_url = api_base_url or _collector_api_base
        self._scan_state = ScanState()
        self._startup_done = False
        self._stop_event = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._scan_thread: threading.Thread | None = None
        self._config_lock = threading.Lock()

        # Internal event buffer
        self._buffer: list[dict] = []
        self._buffer_lock = threading.Lock()

        # Upload backoff state
        self._consecutive_upload_failures = 0
        self._last_upload_failure_time: float = 0.0
        # Backoff schedule: 30s, 60s, 120s, 300s cap
        self._upload_backoff_schedule = [30, 60, 120, 300]

        # Apply config
        self._apply_config(config)

        # Build proxy-bypassing opener
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        logger.info(
            f"LocalDataCollector initialized: "
            f"{len(config.get('sources', []))} sources, "
            f"scan every {self._scan_interval}s"
        )

    def _apply_config(self, config: dict) -> None:
        """Extract all settings from config dict."""
        self._redact_patterns = _compile_redact_patterns(
            config.get("redact_patterns", [])
        )
        self._skip_files = config.get("skip_files", [])
        self._max_event_size = config.get("max_event_size_bytes", DEFAULT_MAX_EVENT_SIZE)
        self._max_events_per_batch = config.get("max_events_per_batch", DEFAULT_MAX_EVENTS_PER_BATCH)
        self._scan_interval = config.get("poll_interval_seconds",
                                         config.get("scan_interval_seconds", DEFAULT_SCAN_INTERVAL))
        self._max_batch_size_bytes = config.get("max_batch_size_mb", 5) * 1024 * 1024

        default_endpoint = f"{self._api_base_url}/ingest/local-sessions"
        endpoint = config.get("upload_endpoint", default_endpoint)
        if endpoint.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(self._api_base_url)
            endpoint = f"{parsed.scheme}://{parsed.netloc}{endpoint}"
        self._upload_endpoint = endpoint

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._scan_thread and self._scan_thread.is_alive():
            logger.warning("LocalDataCollector already running")
            return

        self._stop_event.clear()

        # Start watcher thread (watchfiles or polling fallback)
        if HAS_WATCHFILES:
            self._watcher_thread = threading.Thread(
                target=self._watch_loop,
                daemon=True,
                name="oximy-local-watcher",
            )
            self._watcher_thread.start()

            # Periodic scan thread as safety net (only needed with watchfiles;
            # poll fallback already does full scans every cycle).
            self._scan_thread = threading.Thread(
                target=self._scan_loop,
                daemon=True,
                name="oximy-local-scanner",
            )
            self._scan_thread.start()
        else:
            logger.warning("watchfiles not available, using polling fallback")
            self._watcher_thread = threading.Thread(
                target=self._poll_loop,
                daemon=True,
                name="oximy-local-poller",
            )
            self._watcher_thread.start()
        logger.info("LocalDataCollector started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=5)
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5)
        # Final flush
        self._upload_buffer()
        self._scan_state.save()
        logger.info("LocalDataCollector stopped")

    def update_config(self, config: dict) -> None:
        with self._config_lock:
            if self._config == config:
                return  # No change
            self._config = config
            self._apply_config(config)
        logger.info("LocalDataCollector config updated")

    # ------------------------------------------------------------------
    # Watcher thread (watchfiles)
    # ------------------------------------------------------------------

    def _get_watch_paths(self) -> list[str]:
        """Build list of directories to watch from enabled sources."""
        with self._config_lock:
            sources = self._config.get("sources", [])

        paths = []
        for source in sources:
            if not source.get("enabled", True):
                continue
            detect_path = source.get("detect_path", "")
            if detect_path:
                expanded = detect_path.replace("~", str(Path.home()))
                if os.path.isdir(expanded):
                    paths.append(expanded)
            # Also watch SQLite database parent directories
            for db_config in source.get("sqlite", []):
                db_path = db_config["db_path"].replace("~", str(Path.home()))
                db_path = os.path.expandvars(db_path)
                parent = os.path.dirname(db_path)
                if os.path.isdir(parent) and parent not in paths:
                    paths.append(parent)
        return paths

    def _watch_loop(self) -> None:
        """Background thread: watchfiles-based near-real-time detection."""
        while not self._stop_event.is_set():
            watch_paths = self._get_watch_paths()
            if not watch_paths:
                if self._stop_event.wait(timeout=10):
                    break
                continue

            try:
                for changes in watch(
                    *watch_paths,
                    stop_event=self._stop_event,
                    recursive=True,
                    debounce=100,
                    step=50,
                ):
                    if self._stop_event.is_set():
                        break
                    for change_type, changed_path in changes:
                        if change_type == Change.deleted:
                            continue
                        self._handle_file_change(changed_path)
                    # Upload after processing batch of changes
                    self._upload_buffer()
                    self._scan_state.save()
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Watcher error, restarting in 5s: {e}")
                    if self._stop_event.wait(timeout=5):
                        break

    def _handle_file_change(self, filepath: str) -> None:
        """Process a single file change event from the watcher."""
        if not os.path.isfile(filepath):
            return

        filename = os.path.basename(filepath)
        if _should_skip_file(filename, self._skip_files):
            return

        # Check if this is a SQLite database change
        if self._is_watched_sqlite_db(filepath):
            self._handle_sqlite_change(filepath)
            return

        resolved = self._resolve_change_to_source(filepath)
        if not resolved:
            return

        source_name, file_type, read_mode = resolved

        try:
            if read_mode == "full":
                self._read_full_file(source_name, filepath, file_type)
            else:
                self._read_incremental(source_name, filepath, file_type)
        except (IOError, OSError) as e:
            logger.debug(f"Could not read changed file {filepath}: {e}")

    def _resolve_change_to_source(self, filepath: str) -> tuple[str, str, str] | None:
        """Map a changed file path to its source name, file_type, and read_mode."""
        with self._config_lock:
            sources = self._config.get("sources", [])

        for source in sources:
            if not source.get("enabled", True):
                continue
            source_name = source["name"]
            for glob_config in source.get("globs", []):
                pattern = glob_config["pattern"].replace("~", str(Path.home()))
                skip_patterns = glob_config.get("skip_patterns", [])

                if skip_patterns and any(
                    fnmatch.fnmatch(filepath, sp.replace("~", str(Path.home())))
                    for sp in skip_patterns
                ):
                    continue

                if self._path_matches_pattern(filepath, pattern):
                    return (
                        source_name,
                        glob_config["file_type"],
                        glob_config.get("read_mode", "incremental"),
                    )
        return None

    @staticmethod
    def _path_matches_pattern(filepath: str, pattern: str) -> bool:
        """Check if a filepath matches a glob-style pattern."""
        return fnmatch.fnmatch(filepath, pattern)

    # ------------------------------------------------------------------
    # Polling fallback (when watchfiles unavailable)
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Fallback: poll tracked files every 3s for changes."""
        while not self._stop_event.is_set():
            self._run_full_scan()
            self._upload_buffer()
            self._scan_state.save()
            if self._stop_event.wait(timeout=DEFAULT_POLL_INTERVAL):
                break

    # ------------------------------------------------------------------
    # Periodic scan thread (safety net + backfill)
    # ------------------------------------------------------------------

    def _scan_loop(self) -> None:
        """Background thread: periodic full scan as safety net."""
        # Immediate first scan (handles backfill)
        self._run_full_scan()
        self._upload_buffer()
        self._scan_state.save()

        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self._scan_interval):
                break
            self._run_full_scan()
            self._upload_buffer()
            self._scan_state.save()

    # ------------------------------------------------------------------
    # Scanning logic
    # ------------------------------------------------------------------

    def _run_full_scan(self) -> None:
        """Execute one full scan cycle across all enabled sources."""
        with self._config_lock:
            config = self._config

        if not config.get("enabled", False):
            return

        is_startup = not self._startup_done

        for source_config in config.get("sources", []):
            if not source_config.get("enabled", True):
                continue
            try:
                self._scan_source(source_config, is_startup)
            except Exception as e:
                logger.warning(f"Error scanning source '{source_config.get('name')}': {e}")

        if is_startup:
            self._startup_done = True
            logger.info(
                "LocalDataCollector startup scan complete — now tracking incrementally"
            )

    def _scan_source(self, source_config: dict, is_startup: bool) -> None:
        """Scan one source (e.g., claude_code) for new data."""
        source_name = source_config["name"]
        detect_path = source_config.get("detect_path", "")

        if detect_path:
            expanded = Path(detect_path.replace("~", str(Path.home())))
            if not expanded.exists():
                return

        for glob_config in source_config.get("globs", []):
            try:
                self._scan_glob(source_name, glob_config, is_startup)
            except Exception as e:
                logger.warning(f"Error scanning glob '{glob_config.get('pattern')}': {e}")

        # Scan SQLite databases
        sqlite_configs = source_config.get("sqlite", [])
        if sqlite_configs:
            try:
                self._scan_sqlite_databases(source_name, sqlite_configs, is_startup)
            except Exception as e:
                logger.warning(f"Error scanning SQLite for '{source_name}': {e}")

    def _scan_glob(self, source_name: str, glob_config: dict, is_startup: bool) -> None:
        """Scan files matching a glob pattern."""
        pattern = glob_config["pattern"].replace("~", str(Path.home()))
        file_type = glob_config["file_type"]
        read_mode = glob_config.get("read_mode", "incremental")
        skip_patterns = glob_config.get("skip_patterns", [])

        matched_files = glob_module.glob(pattern, recursive=True)

        if is_startup:
            logger.info(
                f"[STARTUP] Fast-forwarding {len(matched_files)} file(s) "
                f"for '{source_name}'"
            )

        for filepath in matched_files:
            filename = os.path.basename(filepath)

            if _should_skip_file(filename, self._skip_files):
                continue
            if skip_patterns and any(
                fnmatch.fnmatch(filepath, sp.replace("~", str(Path.home())))
                for sp in skip_patterns
            ):
                continue

            if is_startup:
                # Fast-forward: record current EOF, don't read anything
                try:
                    st = os.stat(filepath)
                    self._scan_state.set_file_state(
                        source_name, filepath, st.st_size, st.st_mtime
                    )
                except OSError:
                    pass
                continue

            try:
                if read_mode == "full":
                    self._read_full_file(source_name, filepath, file_type)
                else:
                    self._read_incremental(source_name, filepath, file_type)
            except (IOError, OSError) as e:
                logger.debug(f"Could not read {filepath}: {e}")

    # ------------------------------------------------------------------
    # SQLite scanning
    # ------------------------------------------------------------------

    def _scan_sqlite_databases(self, source_name: str, sqlite_configs: list[dict], is_startup: bool) -> None:
        """Scan all SQLite databases configured for a source."""
        for db_config in sqlite_configs:
            try:
                self._scan_sqlite_db(source_name, db_config, is_startup)
            except Exception as e:
                db_path = db_config.get("db_path", "?")
                logger.warning(f"Error scanning SQLite DB '{db_path}': {e}")

    def _scan_sqlite_db(self, source_name: str, db_config: dict, is_startup: bool) -> None:
        """Open one SQLite database, resolve query order, execute queries."""
        raw_path = db_config["db_path"].replace("~", str(Path.home()))
        db_path = os.path.expandvars(raw_path)

        if not os.path.isfile(db_path):
            return

        try:
            current_mtime = os.stat(db_path).st_mtime
        except OSError:
            return

        # Also check WAL file for changes (SQLite WAL mode)
        wal_path = db_path + "-wal"
        try:
            wal_mtime = os.stat(wal_path).st_mtime
            current_mtime = max(current_mtime, wal_mtime)
        except OSError:
            pass

        db_key = os.path.basename(db_path)
        db_state = self._scan_state.get_sqlite_state(source_name, db_key)
        saved_mtime = db_state.get("mtime", 0)
        mtime_changed = current_mtime != saved_mtime

        queries = db_config.get("queries", [])
        has_incremental = any(q.get("incremental_field") for q in queries)

        # Skip entirely if mtime unchanged and no incremental queries
        if not is_startup and not mtime_changed and not has_incremental:
            return

        try:
            ordered_queries = _resolve_query_order(queries)
        except ValueError as e:
            logger.warning(f"Query ordering error for {db_path}: {e}")
            return

        uri = f"file:{db_path}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=5)
        except sqlite3.Error as e:
            logger.warning(f"Could not open SQLite DB {db_path}: {e}")
            if oximy_log and EventCode:
                oximy_log(EventCode.COLLECT_FAIL_203, "SQLite DB open failed", data={"db": os.path.basename(db_path), "error": str(e)})
            return

        try:
            for query_config in ordered_queries:
                is_incremental = bool(query_config.get("incremental_field"))

                # Non-incremental queries: only run when mtime changes or on startup
                if not is_incremental and not mtime_changed and not is_startup:
                    continue

                # Startup seeding: skip non-incremental queries (nothing to seed)
                if is_startup and not is_incremental:
                    continue

                try:
                    self._execute_sqlite_query(
                        conn, source_name, db_path, db_key, query_config, db_state,
                        seed_only=is_startup,
                    )
                except sqlite3.DatabaseError as e:
                    logger.warning(f"SQLite query error in {db_path}: {e}")
                    if oximy_log and EventCode:
                        oximy_log(EventCode.COLLECT_FAIL_203, "SQLite query error", data={"db": os.path.basename(db_path), "error": str(e)})
                    break
                except Exception as e:
                    logger.warning(
                        f"Error executing query '{query_config.get('file_type')}' "
                        f"on {db_path}: {e}"
                    )
        finally:
            conn.close()

        self._scan_state.set_sqlite_mtime(source_name, db_key, current_mtime)

    def _execute_sqlite_query(
        self,
        conn: sqlite3.Connection,
        source_name: str,
        db_path: str,
        db_key: str,
        query_config: dict,
        db_state: dict,
        seed_only: bool = False,
    ) -> None:
        """Execute one SQLite query, build envelopes for each row.

        If seed_only=True, only captures the max incremental value
        without buffering any rows (used for backfill-disabled seeding).
        """
        file_type = query_config["file_type"]
        sql = query_config["sql"]
        incremental_field = query_config.get("incremental_field")

        # Get saved incremental value for filtering
        saved_inc_value = None
        params: tuple = ()
        if incremental_field:
            saved_inc_value = (
                db_state
                .get("incremental", {})
                .get(file_type, {})
                .get("last_value")
            )
            if "?" in sql:
                params = (saved_inc_value or 0,)

        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Build source_file for envelope
        home = str(Path.home())
        if db_path.startswith(home):
            source_file = "~" + db_path[len(home):]
        else:
            source_file = db_path

        max_incremental_value = None
        row_count = 0

        for row in cursor:
            row_dict = dict(zip(columns, row))

            # Track max incremental value
            if incremental_field:
                inc_val = self._get_incremental_value(row_dict, incremental_field)
                if inc_val is not None:
                    if max_incremental_value is None or inc_val > max_incremental_value:
                        max_incremental_value = inc_val

                    # Client-side filter: skip rows already seen (for queries
                    # without ? in SQL that can't filter at the DB level)
                    if saved_inc_value is not None and inc_val <= saved_inc_value:
                        continue

            # seed_only: just capture the max incremental value, don't buffer rows
            if seed_only:
                row_count += 1
                continue

            raw_line = json.dumps(row_dict, separators=(",", ":"), default=str)
            if len(raw_line.encode("utf-8")) > self._max_event_size:
                logger.debug(f"Skipping oversized SQLite row from {db_path}")
                continue

            raw_line = redact_sensitive(raw_line, self._redact_patterns)

            try:
                raw_obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            timestamp = self._extract_timestamp(raw_obj, db_path)

            envelope: dict[str, Any] = {
                "event_id": generate_event_id(),
                "timestamp": timestamp,
                "type": "local_session",
                "device_id": self._device_id,
                "source": source_name,
                "source_file": source_file,
                "file_type": file_type,
                "raw": raw_obj,
            }

            with self._buffer_lock:
                self._buffer.append(envelope)
            row_count += 1

            with self._buffer_lock:
                buf_size = len(self._buffer)
            if buf_size >= self._max_events_per_batch:
                self._upload_buffer()

        if incremental_field and max_incremental_value is not None:
            self._scan_state.set_sqlite_incremental(
                source_name, db_key, file_type, max_incremental_value
            )

        if row_count > 0:
            db_name = os.path.basename(db_path)
            if seed_only:
                logger.info(
                    f"[BACKFILL] Seeded {db_name}:{file_type} — skipped {row_count} existing row(s)"
                )
            else:
                logger.info(
                    f"[ACTIVE] {source_name}: {row_count} new row(s) from {db_name}:{file_type}"
                )

    @staticmethod
    def _get_incremental_value(row_dict: dict, incremental_field: str) -> Any:
        """Extract the incremental tracking value from a result row.

        The incremental_field might be a plain column name like 'createdAt'
        or an expression like "json_extract(value, '$.createdAt')".
        SQLite names result columns after the expression text.
        """
        # Direct column name match
        if incremental_field in row_dict:
            return row_dict[incremental_field]

        # Expression match: check if incremental_field appears in column names
        for col_name, val in row_dict.items():
            if incremental_field in col_name or col_name in incremental_field:
                return val

        return None

    def _is_watched_sqlite_db(self, filepath: str) -> bool:
        """Check if filepath matches any configured SQLite database path."""
        with self._config_lock:
            sources = self._config.get("sources", [])
        abs_path = os.path.abspath(filepath)
        for source in sources:
            if not source.get("enabled", True):
                continue
            for db_config in source.get("sqlite", []):
                db_path = db_config["db_path"].replace("~", str(Path.home()))
                db_path = os.path.expandvars(db_path)
                if abs_path == os.path.abspath(db_path):
                    return True
        return False

    def _handle_sqlite_change(self, filepath: str) -> None:
        """Handle a change to a watched SQLite database file."""
        with self._config_lock:
            sources = self._config.get("sources", [])
        abs_path = os.path.abspath(filepath)
        for source in sources:
            if not source.get("enabled", True):
                continue
            for db_config in source.get("sqlite", []):
                db_path = db_config["db_path"].replace("~", str(Path.home()))
                db_path = os.path.expandvars(db_path)
                if abs_path == os.path.abspath(db_path):
                    try:
                        self._scan_sqlite_db(source["name"], db_config, is_startup=False)
                    except Exception as e:
                        logger.warning(f"Error on SQLite change {filepath}: {e}")
                    return

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    def _read_incremental(self, source_name: str, filepath: str, file_type: str) -> None:
        """Read new lines from a JSONL file using byte offset tracking."""
        try:
            stat_result = os.stat(filepath)
        except OSError:
            return

        current_mtime = stat_result.st_mtime
        current_size = stat_result.st_size

        state = self._scan_state.get_file_state(source_name, filepath)
        saved_offset = state.get("offset", 0)
        saved_mtime = state.get("mtime", 0)

        # Skip if unchanged
        if current_mtime == saved_mtime and saved_offset >= current_size:
            return

        # File shrank — reset offset
        if saved_offset > current_size:
            logger.info(f"File shrank, resetting offset: {filepath}")
            saved_offset = 0

        new_offset = saved_offset
        line_number = 0

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(saved_offset)

            while True:
                line = f.readline()
                if not line:
                    break

                # Skip partial lines at EOF
                if not line.endswith("\n") and f.tell() >= current_size:
                    break

                line_number += 1
                new_offset = f.tell()

                stripped = line.strip()
                if not stripped:
                    continue

                self._process_line(
                    source_name=source_name,
                    filepath=filepath,
                    file_type=file_type,
                    raw_line=stripped,
                    line_number=line_number,
                )

        if line_number > 0:
            short_path = os.path.basename(os.path.dirname(filepath)) + "/" + os.path.basename(filepath)
            logger.info(
                f"[ACTIVE] {source_name}: {line_number} new event(s) in {short_path}"
            )

        self._scan_state.set_file_state(source_name, filepath, new_offset, current_mtime)

    def _read_full_file(self, source_name: str, filepath: str, file_type: str) -> None:
        """Read entire file (for JSON files like sessions-index.json)."""
        try:
            stat_result = os.stat(filepath)
        except OSError:
            return

        current_mtime = stat_result.st_mtime

        state = self._scan_state.get_file_state(source_name, filepath)
        saved_mtime = state.get("mtime", 0)

        if current_mtime == saved_mtime:
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (IOError, OSError) as e:
            logger.debug(f"Could not read {filepath}: {e}")
            return

        if not content.strip():
            return

        self._process_line(
            source_name=source_name,
            filepath=filepath,
            file_type=file_type,
            raw_line=content.strip(),
            line_number=0,
        )

        self._scan_state.set_file_state(source_name, filepath, 0, current_mtime)

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def _process_line(
        self,
        source_name: str,
        filepath: str,
        file_type: str,
        raw_line: str,
        line_number: int,
    ) -> None:
        """Redact, validate, wrap in envelope, and buffer a single record."""
        # Size check
        if len(raw_line.encode("utf-8")) > self._max_event_size:
            logger.debug(f"Skipping oversized event ({len(raw_line)} bytes) from {filepath}")
            return

        # Redact
        raw_line = redact_sensitive(raw_line, self._redact_patterns)

        # Parse JSON
        try:
            raw_obj = json.loads(raw_line)
        except json.JSONDecodeError:
            logger.debug(f"Skipping non-JSON line in {filepath}:{line_number}")
            return

        # Extract timestamp
        timestamp = self._extract_timestamp(raw_obj, filepath)

        # Path metadata
        path_meta = _extract_metadata_from_path(filepath, source_name)

        # Build envelope
        envelope: dict[str, Any] = {
            "event_id": generate_event_id(),
            "timestamp": timestamp,
            "type": "local_session",
            "device_id": self._device_id,
            "source": source_name,
            "source_file": path_meta["source_file"],
            "file_type": file_type,
            "raw": raw_obj,
        }

        if "project_key" in path_meta:
            envelope["project_key"] = path_meta["project_key"]
        if "session_id" in path_meta:
            envelope["session_id"] = path_meta["session_id"]
        if line_number > 0:
            envelope["line_number"] = line_number

        with self._buffer_lock:
            self._buffer.append(envelope)

        # Trigger upload if buffer is full
        with self._buffer_lock:
            buf_size = len(self._buffer)
        if buf_size >= self._max_events_per_batch:
            self._upload_buffer()

    @staticmethod
    def _strip_tz_suffix(iso: str) -> str:
        """Strip timezone suffix for ClickHouse compatibility.

        ClickHouse DateTime columns cannot parse 'Z' or '+00:00' suffixes.
        All timestamps are already UTC so the suffix is redundant.
        """
        if iso.endswith("Z"):
            return iso[:-1]
        if iso.endswith("+00:00"):
            return iso[:-6]
        return iso

    @staticmethod
    def _extract_timestamp(raw_obj: Any, filepath: str) -> str:
        """Extract timestamp from raw record or fall back to file mtime."""
        ts = None
        if isinstance(raw_obj, dict):
            ts = raw_obj.get("timestamp")

        if ts is None:
            try:
                mtime = os.path.getmtime(filepath)
                return LocalDataCollector._strip_tz_suffix(
                    datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                )
            except OSError:
                return LocalDataCollector._strip_tz_suffix(
                    datetime.now(timezone.utc).isoformat()
                )

        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000
            return LocalDataCollector._strip_tz_suffix(
                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            )

        # Already a string (ISO 8601) — strip tz suffix for ClickHouse
        return LocalDataCollector._strip_tz_suffix(str(ts))

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _upload_buffer(self) -> bool:
        """Upload buffered events to API as gzipped JSONL."""
        with self._buffer_lock:
            if not self._buffer:
                return True

        # Backoff check: skip upload if cooling down after consecutive failures
        if self._consecutive_upload_failures > 0:
            idx = min(
                self._consecutive_upload_failures - 1,
                len(self._upload_backoff_schedule) - 1,
            )
            cooldown = self._upload_backoff_schedule[idx]
            elapsed = time.time() - self._last_upload_failure_time
            if elapsed < cooldown:
                return False

        with self._buffer_lock:
            batch = self._buffer[: self._max_events_per_batch]
            self._buffer = self._buffer[self._max_events_per_batch :]

        token = self._get_device_token()

        payload = "\n".join(
            json.dumps(e, separators=(",", ":")) for e in batch
        )
        compressed = gzip.compress(payload.encode("utf-8"))

        # Split if too large
        if len(compressed) > self._max_batch_size_bytes:
            mid = len(batch) // 2
            with self._buffer_lock:
                self._buffer = batch[mid:] + self._buffer
            batch = batch[:mid]
            payload = "\n".join(
                json.dumps(e, separators=(",", ":")) for e in batch
            )
            compressed = gzip.compress(payload.encode("utf-8"))

        sources = sorted(set(e.get("source", "") for e in batch))

        headers = {
            "Content-Type": "application/jsonl",
            "Content-Encoding": "gzip",
            "User-Agent": "Oximy-Sensor/1.0",
            "X-Oximy-Batch-Size": str(len(batch)),
            "X-Oximy-Sources": ",".join(sources),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        retry_delays = [0.5, 1.0, 2.0]
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    self._upload_endpoint,
                    data=compressed,
                    headers=headers,
                    method="POST",
                )
                with self._opener.open(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                    data = json.loads(body)
                    if data.get("success"):
                        # Log source/file breakdown so we can see what's being uploaded
                        from collections import Counter
                        file_counts = Counter(
                            e.get("source_file", "unknown")
                            for e in batch
                        )
                        breakdown = ", ".join(
                            f"{os.path.basename(f)}({n})"
                            for f, n in file_counts.most_common(5)
                        )
                        if len(file_counts) > 5:
                            breakdown += f", +{len(file_counts) - 5} more"
                        logger.info(
                            f"Uploaded {len(batch)} local session events "
                            f"({len(compressed)} bytes compressed) "
                            f"[{', '.join(sources)}] — {breakdown}"
                        )
                        self._consecutive_upload_failures = 0
                        return True
                    else:
                        logger.warning(f"Upload rejected: {data.get('error')}")
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    logger.warning("Local session upload auth failed (401)")
                    if oximy_log and EventCode:
                        oximy_log(EventCode.COLLECT_FAIL_202, "Local session upload auth failed", data={"status": 401})
                    break
                logger.warning(f"Upload attempt {attempt + 1} failed: HTTP {e.code}")
            except (urllib.error.URLError, OSError) as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")

            if attempt < 2:
                time.sleep(retry_delays[attempt])

        # All retries failed — return batch to buffer with backoff
        self._consecutive_upload_failures += 1
        self._last_upload_failure_time = time.time()
        idx = min(
            self._consecutive_upload_failures - 1,
            len(self._upload_backoff_schedule) - 1,
        )
        next_retry = self._upload_backoff_schedule[idx]
        with self._buffer_lock:
            buf_total = len(batch) + len(self._buffer)
            self._buffer = batch + self._buffer
        logger.warning(
            f"Upload failed ({self._consecutive_upload_failures} consecutive), "
            f"{buf_total} events buffered, next retry in {next_retry}s "
            f"(endpoint: {self._upload_endpoint})"
        )
        if oximy_log and EventCode:
            oximy_log(EventCode.COLLECT_FAIL_202, "Local session upload failed", data={
                "consecutive_failures": self._consecutive_upload_failures,
                "buffered_events": buf_total,
                "next_retry_s": next_retry,
            })
        return False

    @staticmethod
    def _get_device_token() -> str | None:
        try:
            if OXIMY_TOKEN_FILE.exists():
                token = OXIMY_TOKEN_FILE.read_text().strip()
                if token:
                    return token
        except (IOError, OSError):
            pass
        return None

    # ------------------------------------------------------------------
    # Heartbeat helper
    # ------------------------------------------------------------------

    def get_installed_tools(self) -> dict[str, bool]:
        """Check which tools are installed (for heartbeat reporting)."""
        with self._config_lock:
            sources = self._config.get("sources", [])

        result = {}
        for source in sources:
            name = source.get("name", "")
            detect_path = source.get("detect_path", "")
            if detect_path:
                expanded = Path(detect_path.replace("~", str(Path.home())))
                result[name] = expanded.exists()
            else:
                result[name] = False
        return result
