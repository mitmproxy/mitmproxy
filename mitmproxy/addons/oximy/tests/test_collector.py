"""Tests for LocalDataCollector — local AI session file ingestion."""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mitmproxy.addons.oximy.collector import (
    LocalDataCollector,
    ScanState,
    redact_sensitive,
    _compile_redact_patterns,
    _should_skip_file,
    _extract_metadata_from_path,
    _resolve_query_order,
    DEFAULT_MAX_EVENT_SIZE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_oximy_dir(tmp_path):
    """Override OXIMY paths to use temp directory."""
    return tmp_path / ".oximy"


@pytest.fixture
def scan_state(tmp_path):
    """ScanState backed by a temp file."""
    return ScanState(state_file=tmp_path / "scan-state.json")


@pytest.fixture
def sample_config(tmp_path):
    """Minimal localDataSources config for testing."""
    projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-myproject"
    projects_dir.mkdir(parents=True)
    return {
        "enabled": True,
        "poll_interval_seconds": 1,
        "scan_interval_seconds": 60,
        "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
        "max_batch_size_mb": 5,
        "max_events_per_batch": 200,
        "backfill_max_age_days": 7,
        "sources": [
            {
                "name": "claude_code",
                "enabled": True,
                "globs": [
                    {
                        "pattern": str(tmp_path / ".claude" / "projects" / "*" / "*.jsonl"),
                        "file_type": "session_transcript",
                    }
                ],
                "detect_path": str(tmp_path / ".claude" / "projects"),
            }
        ],
        "redact_patterns": [
            r"sk-[a-zA-Z0-9]{20,}",
            r"ghp_[a-zA-Z0-9]{36,}",
        ],
        "skip_files": ["*auth*", "*token*", "*.pem"],
        "max_event_size_bytes": DEFAULT_MAX_EVENT_SIZE,
    }


@pytest.fixture
def collector(sample_config):
    """LocalDataCollector instance (not started)."""
    with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", Path("/tmp/test-scan-state.json")):
        c = LocalDataCollector(config=sample_config, device_id="test-device-123")
    return c


def _write_jsonl(filepath, records):
    """Write a list of dicts as JSONL to filepath."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


# ===========================================================================
# TestRedactSensitive
# ===========================================================================

class TestRedactSensitive:
    """Tests for regex-based redaction on raw JSON strings."""

    def setup_method(self):
        self.patterns = _compile_redact_patterns([
            r"sk-[a-zA-Z0-9]{20,}",
            r"anthropic-[a-zA-Z0-9]{20,}",
            r"ghp_[a-zA-Z0-9]{36,}",
            r"Bearer\s+[a-zA-Z0-9._-]{20,}",
            r"ya29\.[a-zA-Z0-9._-]+",
            r"eyJ[a-zA-Z0-9._-]{40,}",
        ])

    def test_redacts_openai_api_key(self):
        line = '{"key": "sk-abcdefghij1234567890abcdef"}'
        result = redact_sensitive(line, self.patterns)
        assert "sk-abcdefghij" not in result
        assert "[REDACTED]" in result

    def test_redacts_anthropic_key(self):
        line = '{"api_key": "anthropic-abcdefghij1234567890"}'
        result = redact_sensitive(line, self.patterns)
        assert "anthropic-abcdefghij" not in result
        assert "[REDACTED]" in result

    def test_redacts_github_token(self):
        line = '{"token": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}'
        result = redact_sensitive(line, self.patterns)
        assert "ghp_" not in result
        assert "[REDACTED]" in result

    def test_redacts_bearer_token(self):
        line = '{"auth": "Bearer eyJhbGciOiJIUzI1NiJ9.test"}'
        result = redact_sensitive(line, self.patterns)
        assert "Bearer eyJ" not in result

    def test_redacts_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w"
        line = f'{{"token": "{jwt}"}}'
        result = redact_sensitive(line, self.patterns)
        assert "eyJhbGciOiJ" not in result

    def test_no_redaction_for_normal_text(self):
        line = '{"message": "Hello, world!", "count": 42}'
        result = redact_sensitive(line, self.patterns)
        assert result == line

    def test_multiple_patterns_in_one_line(self):
        line = '{"key1": "sk-abcdefghij1234567890abcdef", "key2": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"}'
        result = redact_sensitive(line, self.patterns)
        assert "sk-" not in result
        assert "ghp_" not in result
        assert result.count("[REDACTED]") == 2

    def test_invalid_pattern_handled(self):
        patterns = _compile_redact_patterns(["[invalid", "sk-[a-zA-Z0-9]{20,}"])
        assert len(patterns) == 1  # Invalid pattern skipped
        line = '{"key": "sk-abcdefghij1234567890abcdef"}'
        result = redact_sensitive(line, patterns)
        assert "[REDACTED]" in result


# ===========================================================================
# TestShouldSkipFile
# ===========================================================================

class TestShouldSkipFile:
    def test_skip_auth_file(self):
        assert _should_skip_file("auth.json", ["*auth*"]) is True

    def test_skip_pem_file(self):
        assert _should_skip_file("server.pem", ["*.pem"]) is True

    def test_skip_token_file(self):
        assert _should_skip_file("device-token.txt", ["*token*"]) is True

    def test_no_skip_normal_file(self):
        assert _should_skip_file("session.jsonl", ["*auth*", "*.pem"]) is False

    def test_empty_patterns(self):
        assert _should_skip_file("anything.json", []) is False


# ===========================================================================
# TestExtractMetadataFromPath
# ===========================================================================

class TestExtractMetadataFromPath:
    def test_claude_code_session_path(self):
        home = str(Path.home())
        path = f"{home}/.claude/projects/-Users-test-myproject/abc123.jsonl"
        meta = _extract_metadata_from_path(path, "claude_code")
        assert meta["source_file"] == "~/.claude/projects/-Users-test-myproject/abc123.jsonl"
        assert meta["project_key"] == "-Users-test-myproject"
        assert meta["session_id"] == "abc123"

    def test_claude_code_subagent_path(self):
        home = str(Path.home())
        path = f"{home}/.claude/projects/-Users-test/sess1/subagents/agent-abc.jsonl"
        meta = _extract_metadata_from_path(path, "claude_code")
        assert meta["project_key"] == "-Users-test"
        assert meta["session_id"] == "agent-abc"

    def test_claude_code_sessions_index(self):
        home = str(Path.home())
        path = f"{home}/.claude/projects/-Users-test/sessions-index.json"
        meta = _extract_metadata_from_path(path, "claude_code")
        assert meta["project_key"] == "-Users-test"
        assert "session_id" not in meta  # Index file has no session_id

    def test_claude_code_history(self):
        home = str(Path.home())
        path = f"{home}/.claude/history.jsonl"
        meta = _extract_metadata_from_path(path, "claude_code")
        assert meta["source_file"] == "~/.claude/history.jsonl"
        assert "project_key" not in meta
        assert "session_id" not in meta  # No "projects" in path → no extraction

    def test_source_file_relative_to_home(self):
        home = str(Path.home())
        path = f"{home}/some/deep/path/file.jsonl"
        meta = _extract_metadata_from_path(path, "cursor")
        assert meta["source_file"].startswith("~/")

    def test_path_outside_home(self):
        path = "/tmp/test/file.jsonl"
        meta = _extract_metadata_from_path(path, "cursor")
        assert meta["source_file"] == "/tmp/test/file.jsonl"

    def test_unknown_source_minimal_metadata(self):
        home = str(Path.home())
        path = f"{home}/unknown/path/file.jsonl"
        meta = _extract_metadata_from_path(path, "some_future_tool")
        assert "source_file" in meta
        assert "project_key" not in meta
        assert "session_id" not in meta

    def test_stats_cache_no_session_id(self):
        home = str(Path.home())
        path = f"{home}/.claude/stats-cache.json"
        meta = _extract_metadata_from_path(path, "claude_code")
        assert "session_id" not in meta


# ===========================================================================
# TestScanState
# ===========================================================================

class TestScanState:
    def test_initial_state_empty(self, scan_state):
        assert scan_state.get_file_state("claude_code", "/some/file.jsonl") == {}

    def test_set_and_get_file_state(self, scan_state):
        scan_state.set_file_state("claude_code", "/file.jsonl", 1234, 1700000000.0)
        state = scan_state.get_file_state("claude_code", "/file.jsonl")
        assert state["offset"] == 1234
        assert state["mtime"] == 1700000000.0

    def test_save_and_load(self, tmp_path):
        state_file = tmp_path / "state.json"
        s1 = ScanState(state_file=state_file)
        s1.set_file_state("claude_code", "/file.jsonl", 500, 1700000000.0)
        s1.save()

        s2 = ScanState(state_file=state_file)
        state = s2.get_file_state("claude_code", "/file.jsonl")
        assert state["offset"] == 500
        assert state["mtime"] == 1700000000.0

    def test_file_not_tracked(self, scan_state):
        scan_state.set_file_state("claude_code", "/file1.jsonl", 100, 1.0)
        assert scan_state.get_file_state("claude_code", "/file2.jsonl") == {}

    def test_multiple_sources(self, scan_state):
        scan_state.set_file_state("claude_code", "/file.jsonl", 100, 1.0)
        scan_state.set_file_state("cursor", "/file.jsonl", 200, 2.0)
        assert scan_state.get_file_state("claude_code", "/file.jsonl")["offset"] == 100
        assert scan_state.get_file_state("cursor", "/file.jsonl")["offset"] == 200

    def test_corrupt_state_file(self, tmp_path):
        state_file = tmp_path / "corrupt.json"
        state_file.write_text("{ this is not valid json !!!")
        s = ScanState(state_file=state_file)
        assert s.get_file_state("any", "any") == {}

    def test_version_mismatch(self, tmp_path):
        state_file = tmp_path / "old_version.json"
        state_file.write_text(json.dumps({"version": 99, "sources": {"a": {"files": {"f": {"offset": 1}}}}}))
        s = ScanState(state_file=state_file)
        assert s.get_file_state("a", "f") == {}  # Version mismatch → fresh start

    def test_is_first_run(self, scan_state):
        assert scan_state.is_first_run() is True
        scan_state.set_file_state("claude_code", "/f.jsonl", 100, 1.0)
        assert scan_state.is_first_run() is False


# ===========================================================================
# TestLocalDataCollectorRead
# ===========================================================================

class TestLocalDataCollectorRead:
    """Tests for incremental and full file reading."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        self.projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="test-device")

    def test_read_incremental_new_file(self):
        fp = str(self.projects_dir / "sess1.jsonl")
        _write_jsonl(fp, [{"message": "hello", "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")

        assert len(self.collector._buffer) == 1
        event = self.collector._buffer[0]
        assert event["type"] == "local_session"
        assert event["source"] == "claude_code"
        assert event["raw"]["message"] == "hello"

    def test_read_incremental_resume(self):
        fp = str(self.projects_dir / "sess2.jsonl")
        _write_jsonl(fp, [
            {"message": "line1", "timestamp": "2025-01-01T00:00:00Z"},
            {"message": "line2", "timestamp": "2025-01-01T00:00:01Z"},
        ])

        # First read: gets both lines
        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 2

        # Append a new line
        with open(fp, "a") as f:
            f.write(json.dumps({"message": "line3", "timestamp": "2025-01-01T00:00:02Z"}) + "\n")

        # Update mtime so it's detected
        self.collector._buffer.clear()
        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["message"] == "line3"

    def test_read_incremental_file_unchanged(self):
        fp = str(self.projects_dir / "sess3.jsonl")
        _write_jsonl(fp, [{"message": "data", "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 1

        # Second read: same mtime, same size → nothing new
        self.collector._buffer.clear()
        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 0

    def test_read_incremental_file_shrank(self):
        fp = str(self.projects_dir / "sess4.jsonl")
        _write_jsonl(fp, [
            {"message": "line1"},
            {"message": "line2"},
            {"message": "line3"},
        ])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 3

        # Truncate file
        with open(fp, "w") as f:
            f.write(json.dumps({"message": "new_only"}) + "\n")

        self.collector._buffer.clear()
        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["message"] == "new_only"

    def test_read_incremental_partial_line(self):
        fp = str(self.projects_dir / "partial.jsonl")
        with open(fp, "w") as f:
            f.write(json.dumps({"message": "complete"}) + "\n")
            f.write('{"message": "incomple')  # No trailing newline

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["message"] == "complete"

    def test_read_incremental_skips_non_json(self):
        fp = str(self.projects_dir / "mixed.jsonl")
        with open(fp, "w") as f:
            f.write(json.dumps({"message": "valid"}) + "\n")
            f.write("this is not json\n")
            f.write(json.dumps({"message": "also_valid"}) + "\n")

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 2

    def test_read_incremental_skips_empty_lines(self):
        fp = str(self.projects_dir / "empty_lines.jsonl")
        with open(fp, "w") as f:
            f.write(json.dumps({"message": "data"}) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps({"message": "more"}) + "\n")

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 2

    def test_read_full_file(self):
        fp = str(self.projects_dir / "sessions-index.json")
        with open(fp, "w") as f:
            json.dump({"sessions": [{"id": "abc"}]}, f)

        self.collector._read_full_file("claude_code", fp, "session_index")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["sessions"][0]["id"] == "abc"

    def test_read_full_file_unchanged_mtime(self):
        fp = str(self.projects_dir / "index2.json")
        with open(fp, "w") as f:
            json.dump({"data": 1}, f)

        self.collector._read_full_file("claude_code", fp, "session_index")
        assert len(self.collector._buffer) == 1

        self.collector._buffer.clear()
        self.collector._read_full_file("claude_code", fp, "session_index")
        assert len(self.collector._buffer) == 0  # Unchanged

    def test_read_full_file_empty(self):
        fp = str(self.projects_dir / "empty.json")
        with open(fp, "w") as f:
            f.write("")

        self.collector._read_full_file("claude_code", fp, "session_index")
        assert len(self.collector._buffer) == 0

    def test_skips_oversized_event(self):
        fp = str(self.projects_dir / "big.jsonl")
        big_data = {"message": "x" * (DEFAULT_MAX_EVENT_SIZE + 100)}
        _write_jsonl(fp, [big_data])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 0

    def test_file_not_found(self):
        self.collector._read_incremental("claude_code", "/nonexistent.jsonl", "session_transcript")
        assert len(self.collector._buffer) == 0

    def test_read_incremental_multiple_reads(self):
        """Simulate a live session with multiple appends."""
        fp = str(self.projects_dir / "live.jsonl")
        _write_jsonl(fp, [{"msg": "first", "timestamp": 1700000000000}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 1

        # Append more
        with open(fp, "a") as f:
            f.write(json.dumps({"msg": "second", "timestamp": 1700000001000}) + "\n")
            f.write(json.dumps({"msg": "third", "timestamp": 1700000002000}) + "\n")

        self.collector._buffer.clear()
        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert len(self.collector._buffer) == 2


# ===========================================================================
# TestLocalDataCollectorEnvelope
# ===========================================================================

class TestLocalDataCollectorEnvelope:
    """Tests for event envelope structure."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        self.projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-proj"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="dev-123")

    def test_envelope_structure(self):
        fp = str(self.projects_dir / "abc123.jsonl")
        _write_jsonl(fp, [{"message": "test", "timestamp": "2025-06-01T12:00:00Z"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        event = self.collector._buffer[0]

        assert event["type"] == "local_session"
        assert event["device_id"] == "dev-123"
        assert event["source"] == "claude_code"
        assert event["file_type"] == "session_transcript"
        assert "event_id" in event
        assert "timestamp" in event
        assert event["raw"]["message"] == "test"

    def test_timestamp_from_iso_string(self):
        fp = str(self.projects_dir / "ts1.jsonl")
        _write_jsonl(fp, [{"timestamp": "2025-06-01T12:00:00Z", "data": 1}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert self.collector._buffer[0]["timestamp"] == "2025-06-01T12:00:00"

    def test_timestamp_from_epoch_ms(self):
        fp = str(self.projects_dir / "ts2.jsonl")
        _write_jsonl(fp, [{"timestamp": 1717200000000, "data": 1}])  # epoch ms

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        ts = self.collector._buffer[0]["timestamp"]
        assert "2024" in ts  # epoch ms 1717200000000 ≈ June 2024
        assert not ts.endswith("Z") and not ts.endswith("+00:00")

    def test_timestamp_from_epoch_seconds(self):
        fp = str(self.projects_dir / "ts3.jsonl")
        _write_jsonl(fp, [{"timestamp": 1717200000, "data": 1}])  # epoch seconds

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        ts = self.collector._buffer[0]["timestamp"]
        assert "2024" in ts
        assert not ts.endswith("Z") and not ts.endswith("+00:00")

    def test_timestamp_fallback_to_mtime(self):
        fp = str(self.projects_dir / "ts4.jsonl")
        _write_jsonl(fp, [{"data": "no_timestamp"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        ts = self.collector._buffer[0]["timestamp"]
        assert ts is not None  # Should use file mtime
        assert not ts.endswith("Z") and not ts.endswith("+00:00")

    def test_project_key_extracted(self):
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert self.collector._buffer[0]["project_key"] == "-Users-test-proj"

    def test_session_id_extracted(self):
        fp = str(self.projects_dir / "my-session-uuid.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert self.collector._buffer[0]["session_id"] == "my-session-uuid"

    def test_line_number_included(self):
        fp = str(self.projects_dir / "ln.jsonl")
        _write_jsonl(fp, [
            {"data": "first", "timestamp": "2025-01-01T00:00:00Z"},
            {"data": "second", "timestamp": "2025-01-01T00:00:01Z"},
        ])

        self.collector._read_incremental("claude_code", fp, "session_transcript")
        assert self.collector._buffer[0]["line_number"] == 1
        assert self.collector._buffer[1]["line_number"] == 2


# ===========================================================================
# TestLocalDataCollectorScan
# ===========================================================================

class TestLocalDataCollectorScan:
    """Tests for source scanning and glob expansion."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        self.projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-proj"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="test-device")
        # Mark startup as done so scans read data normally
        self.collector._startup_done = True

    def test_scan_source_detects_installed(self):
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        source_config = self.collector._config["sources"][0]
        self.collector._scan_source(source_config, is_startup=False)
        assert len(self.collector._buffer) == 1

    def test_scan_source_skips_uninstalled(self):
        source_config = {
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "detect_path": str(self.tmp_path / "nonexistent"),
        }
        self.collector._scan_source(source_config, is_startup=False)
        assert len(self.collector._buffer) == 0

    def test_scan_glob_discovers_files(self):
        for i in range(3):
            fp = str(self.projects_dir / f"sess{i}.jsonl")
            _write_jsonl(fp, [{"msg": f"session{i}", "timestamp": "2025-01-01T00:00:00Z"}])

        source_config = self.collector._config["sources"][0]
        self.collector._scan_source(source_config, is_startup=False)
        assert len(self.collector._buffer) == 3

    def test_scan_skips_disabled_source(self):
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._config["sources"][0]["enabled"] = False
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0

    def test_scan_skips_skip_files(self):
        auth_fp = str(self.projects_dir / "auth_session.jsonl")
        normal_fp = str(self.projects_dir / "normal.jsonl")
        _write_jsonl(auth_fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])
        _write_jsonl(normal_fp, [{"data": 2, "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["data"] == 2

    def test_scan_applies_redaction(self):
        fp = str(self.projects_dir / "secrets.jsonl")
        _write_jsonl(fp, [{"key": "sk-abcdefghijklmnopqrstuvwxyz1234", "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        raw = self.collector._buffer[0]["raw"]
        assert "sk-" not in json.dumps(raw)

    def test_scan_disabled_config(self):
        self.collector._config["enabled"] = False
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1}])

        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0

    def test_full_scan_idempotent(self):
        """Second scan of same files produces no new events."""
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1

        self.collector._buffer.clear()
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0


# ===========================================================================
# TestUploadBuffer
# ===========================================================================

class TestUploadBuffer:
    """Tests for gzipped JSONL upload to API."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path, sample_config):
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="test-device")
        self.token_file = tmp_path / "token"
        self.token_file.write_text("test-token-abc")

    def test_upload_empty_buffer(self):
        assert self.collector._upload_buffer() is True

    def test_upload_gzipped_jsonl(self):
        event = {
            "event_id": "test-id",
            "type": "local_session",
            "source": "claude_code",
            "raw": {"msg": "test"},
        }
        self.collector._buffer = [event]

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value="test-token"):
                result = self.collector._upload_buffer()

        assert result is True
        assert len(self.collector._buffer) == 0

        # Verify request
        req = mock_open.call_args[0][0]
        assert req.get_header("Content-type") == "application/jsonl"
        assert req.get_header("Content-encoding") == "gzip"
        assert req.get_header("Authorization") == "Bearer test-token"

        # Verify payload is valid gzipped JSONL
        decompressed = gzip.decompress(req.data).decode("utf-8")
        parsed = json.loads(decompressed)
        assert parsed["event_id"] == "test-id"

    def test_upload_batch_headers(self):
        events = [
            {"event_id": f"id-{i}", "source": "claude_code", "raw": {}}
            for i in range(5)
        ]
        self.collector._buffer = events

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                self.collector._upload_buffer()

        req = mock_open.call_args[0][0]
        assert req.get_header("X-oximy-batch-size") == "5"
        assert req.get_header("X-oximy-sources") == "claude_code"

    def test_upload_retry_on_failure(self):
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]

        with patch.object(self.collector._opener, "open", side_effect=urllib.error.URLError("conn refused")):
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                with patch("mitmproxy.addons.oximy.collector.time.sleep"):
                    result = self.collector._upload_buffer()

        assert result is False
        assert len(self.collector._buffer) == 1  # Events returned to buffer

    def test_upload_no_retry_on_401(self):
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]

        error_401 = urllib.error.HTTPError(
            url="http://test", code=401, msg="Unauthorized",
            hdrs=None, fp=None  # type: ignore
        )
        with patch.object(self.collector._opener, "open", side_effect=error_401) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value="bad-token"):
                with patch("mitmproxy.addons.oximy.collector.time.sleep"):
                    result = self.collector._upload_buffer()

        assert result is False
        assert mock_open.call_count == 1  # No retries on 401

    def test_upload_events_returned_on_failure(self):
        events = [{"event_id": f"id-{i}", "source": "test", "raw": {}} for i in range(3)]
        self.collector._buffer = events.copy()

        with patch.object(self.collector._opener, "open", side_effect=urllib.error.URLError("fail")):
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                with patch("mitmproxy.addons.oximy.collector.time.sleep"):
                    self.collector._upload_buffer()

        assert len(self.collector._buffer) == 3
        assert self.collector._buffer[0]["event_id"] == "id-0"

    def test_upload_with_no_token(self):
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                result = self.collector._upload_buffer()

        assert result is True
        req = mock_open.call_args[0][0]
        assert not req.has_header("Authorization")

    def test_upload_multiple_sources(self):
        events = [
            {"event_id": "1", "source": "claude_code", "raw": {}},
            {"event_id": "2", "source": "cursor", "raw": {}},
        ]
        self.collector._buffer = events

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                self.collector._upload_buffer()

        req = mock_open.call_args[0][0]
        assert req.get_header("X-oximy-sources") == "claude_code,cursor"

    def test_upload_backoff_after_failure(self):
        """After a failed upload, subsequent calls within cooldown are skipped."""
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]

        with patch.object(self.collector._opener, "open", side_effect=urllib.error.URLError("fail")):
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                with patch("mitmproxy.addons.oximy.collector.time.sleep"):
                    result = self.collector._upload_buffer()

        assert result is False
        assert self.collector._consecutive_upload_failures == 1
        assert self.collector._last_upload_failure_time > 0

        # Next call within cooldown should be skipped (returns False, no HTTP call)
        with patch.object(self.collector._opener, "open") as mock_open:
            result = self.collector._upload_buffer()

        assert result is False
        mock_open.assert_not_called()  # Skipped due to cooldown

    def test_upload_backoff_resets_on_success(self):
        """Successful upload resets the consecutive failure counter."""
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]
        self.collector._consecutive_upload_failures = 3
        self.collector._last_upload_failure_time = 0  # Expired cooldown

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp):
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                result = self.collector._upload_buffer()

        assert result is True
        assert self.collector._consecutive_upload_failures == 0

    def test_upload_backoff_escalates(self):
        """Consecutive failures increase the backoff cooldown."""
        for i in range(4):
            self.collector._buffer = [{"event_id": f"x-{i}", "source": "test", "raw": {}}]
            # Reset cooldown timer so upload is attempted
            self.collector._last_upload_failure_time = 0

            with patch.object(self.collector._opener, "open", side_effect=urllib.error.URLError("fail")):
                with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                    with patch("mitmproxy.addons.oximy.collector.time.sleep"):
                        self.collector._upload_buffer()

        assert self.collector._consecutive_upload_failures == 4
        # 4th failure uses schedule index 3 = 300s cap
        expected_cooldowns = [30, 60, 120, 300]
        assert self.collector._upload_backoff_schedule == expected_cooldowns

    def test_upload_backoff_expires(self):
        """After cooldown expires, upload is retried."""
        self.collector._buffer = [{"event_id": "x", "source": "test", "raw": {}}]
        self.collector._consecutive_upload_failures = 1
        # Set failure time far in the past (cooldown expired)
        self.collector._last_upload_failure_time = time.time() - 100

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(self.collector._opener, "open", return_value=mock_resp) as mock_open:
            with patch.object(LocalDataCollector, "_get_device_token", return_value=None):
                result = self.collector._upload_buffer()

        assert result is True
        mock_open.assert_called_once()
        assert self.collector._consecutive_upload_failures == 0


# ===========================================================================
# TestCollectorLifecycle
# ===========================================================================

class TestCollectorLifecycle:
    def test_start_and_stop(self, tmp_path, sample_config):
        sample_config["enabled"] = False  # Don't actually scan
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "state.json"):
            c = LocalDataCollector(config=sample_config, device_id="dev")

        with patch.object(c, "_upload_buffer"):
            c.start()
            assert c._watcher_thread is not None
            assert c._watcher_thread.is_alive()

            c.stop()
            assert not c._watcher_thread.is_alive()

    def test_stop_flushes_buffer(self, tmp_path, sample_config):
        sample_config["enabled"] = False
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "state.json"):
            c = LocalDataCollector(config=sample_config, device_id="dev")

        c._buffer = [{"event_id": "x", "source": "test", "raw": {}}]

        with patch.object(c, "_upload_buffer") as mock_upload:
            c.start()
            c.stop()
            mock_upload.assert_called()


# ===========================================================================
# TestWatcherIntegration
# ===========================================================================

class TestWatcherIntegration:
    """Tests for file watcher path resolution."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="test-device")

    def test_resolve_change_to_source(self):
        projects_dir = self.tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        fp = str(projects_dir / "session.jsonl")
        result = self.collector._resolve_change_to_source(fp)
        assert result is not None
        source_name, file_type, read_mode, content_type = result
        assert source_name == "claude_code"
        assert file_type == "session_transcript"
        assert read_mode == "incremental"
        assert content_type == "json"

    def test_resolve_no_match(self):
        result = self.collector._resolve_change_to_source("/some/random/file.txt")
        assert result is None

    def test_get_watch_paths(self):
        paths = self.collector._get_watch_paths()
        assert len(paths) >= 0  # May be 0 if detect_path doesn't exist yet

    def test_handle_file_change_reads_new_data(self):
        projects_dir = self.tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        fp = str(projects_dir / "watched.jsonl")
        _write_jsonl(fp, [{"msg": "new_data", "timestamp": "2025-01-01T00:00:00Z"}])

        self.collector._handle_file_change(fp)
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["msg"] == "new_data"

    def test_handle_file_change_skips_skip_files(self):
        projects_dir = self.tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        fp = str(projects_dir / "auth_data.jsonl")
        _write_jsonl(fp, [{"data": 1}])

        self.collector._handle_file_change(fp)
        assert len(self.collector._buffer) == 0  # Skipped by skip_files pattern


# ===========================================================================
# TestStartupFastForward
# ===========================================================================

class TestStartupFastForward:
    """Tests for startup fast-forwarding: first scan records EOF, no data buffered."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        self.projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.sample_config = sample_config

    def test_startup_scan_buffers_nothing(self):
        """First scan (startup) should fast-forward all files to EOF."""
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        # Create files with data
        for i in range(3):
            fp = str(self.projects_dir / f"sess{i}.jsonl")
            _write_jsonl(fp, [{"data": f"d{i}", "timestamp": "2025-01-01T00:00:00Z"}])

        collector._run_full_scan()

        # Nothing should be buffered — startup fast-forwards all files
        assert len(collector._buffer) == 0
        assert collector._startup_done is True

    def test_startup_records_eof(self):
        """Startup scan should record each file at its current size."""
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": "test", "timestamp": "2025-01-01T00:00:00Z"}])

        collector._run_full_scan()

        state = collector._scan_state.get_file_state("claude_code", fp)
        assert state is not None
        assert state["offset"] == os.path.getsize(fp)

    def test_second_scan_reads_incrementally(self):
        """After startup, new data written to files should be captured."""
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": "initial", "timestamp": "2025-01-01T00:00:00Z"}])

        # First scan: fast-forward
        collector._run_full_scan()
        assert len(collector._buffer) == 0

        # Write new data after startup
        with open(fp, "a") as f:
            f.write('{"data": "new_line", "timestamp": "2025-06-01T00:00:00Z"}\n')

        # Second scan: should capture only the new line
        collector._run_full_scan()
        assert len(collector._buffer) == 1
        assert collector._buffer[0]["raw"]["data"] == "new_line"


# ---------------------------------------------------------------------------
# Phase 2: SQLite support tests
# ---------------------------------------------------------------------------

def _create_test_db(db_path, table_name, columns, rows):
    """Create a SQLite database with a single table and insert rows."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    col_defs = ", ".join(f"{c} TEXT" for c in columns)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})")
    placeholders = ", ".join("?" for _ in columns)
    for row in rows:
        conn.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", row)
    conn.commit()
    conn.close()


class TestResolveQueryOrder:
    def test_single_query_no_deps(self):
        queries = [{"file_type": "a", "sql": "SELECT 1"}]
        result = _resolve_query_order(queries)
        assert [q["file_type"] for q in result] == ["a"]

    def test_two_queries_no_deps(self):
        queries = [
            {"file_type": "a", "sql": "SELECT 1"},
            {"file_type": "b", "sql": "SELECT 2"},
        ]
        result = _resolve_query_order(queries)
        assert [q["file_type"] for q in result] == ["a", "b"]

    def test_dependency_ordering(self):
        queries = [
            {"file_type": "b", "sql": "SELECT 2", "depends_on": "a"},
            {"file_type": "a", "sql": "SELECT 1"},
        ]
        result = _resolve_query_order(queries)
        assert [q["file_type"] for q in result] == ["a", "b"]

    def test_chain_dependencies(self):
        queries = [
            {"file_type": "c", "sql": "S3", "depends_on": "b"},
            {"file_type": "b", "sql": "S2", "depends_on": "a"},
            {"file_type": "a", "sql": "S1"},
        ]
        result = _resolve_query_order(queries)
        assert [q["file_type"] for q in result] == ["a", "b", "c"]

    def test_circular_dependency_raises(self):
        queries = [
            {"file_type": "a", "sql": "S1", "depends_on": "b"},
            {"file_type": "b", "sql": "S2", "depends_on": "a"},
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            _resolve_query_order(queries)

    def test_unknown_depends_on_raises(self):
        queries = [
            {"file_type": "a", "sql": "S1", "depends_on": "nonexistent"},
        ]
        with pytest.raises(ValueError, match="Unknown depends_on"):
            _resolve_query_order(queries)

    def test_mixed_deps_and_independent(self):
        queries = [
            {"file_type": "c", "sql": "S3", "depends_on": "a"},
            {"file_type": "a", "sql": "S1"},
            {"file_type": "b", "sql": "S2"},
        ]
        result = _resolve_query_order(queries)
        types = [q["file_type"] for q in result]
        assert types.index("a") < types.index("c")
        assert "b" in types


class TestScanStateSqlite:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.state = ScanState(state_file=tmp_path / "scan-state.json")
        self.tmp_path = tmp_path

    def test_get_sqlite_state_empty(self):
        assert self.state.get_sqlite_state("cursor", "state.vscdb") == {}

    def test_set_and_get_sqlite_mtime(self):
        self.state.set_sqlite_mtime("cursor", "state.vscdb", 1234567890.0)
        st = self.state.get_sqlite_state("cursor", "state.vscdb")
        assert st["mtime"] == 1234567890.0

    def test_set_and_get_incremental(self):
        self.state.set_sqlite_incremental("cursor", "state.vscdb", "sqlite_composer", 999)
        st = self.state.get_sqlite_state("cursor", "state.vscdb")
        assert st["incremental"]["sqlite_composer"]["last_value"] == 999

    def test_multiple_incrementals(self):
        self.state.set_sqlite_incremental("cursor", "db.sqlite", "type_a", 100)
        self.state.set_sqlite_incremental("cursor", "db.sqlite", "type_b", 200)
        st = self.state.get_sqlite_state("cursor", "db.sqlite")
        assert st["incremental"]["type_a"]["last_value"] == 100
        assert st["incremental"]["type_b"]["last_value"] == 200

    def test_sqlite_state_save_and_load(self):
        self.state.set_sqlite_mtime("cursor", "state.vscdb", 111.0)
        self.state.set_sqlite_incremental("cursor", "state.vscdb", "comp", 42)
        self.state.save()

        loaded = ScanState(state_file=self.tmp_path / "scan-state.json")
        st = loaded.get_sqlite_state("cursor", "state.vscdb")
        assert st["mtime"] == 111.0
        assert st["incremental"]["comp"]["last_value"] == 42

    def test_sqlite_and_file_state_coexist(self):
        self.state.set_file_state("cursor", "/some/file.jsonl", 500, 100.0)
        self.state.set_sqlite_mtime("cursor", "state.vscdb", 200.0)
        self.state.save()

        loaded = ScanState(state_file=self.tmp_path / "scan-state.json")
        assert loaded.get_file_state("cursor", "/some/file.jsonl")["offset"] == 500
        assert loaded.get_sqlite_state("cursor", "state.vscdb")["mtime"] == 200.0

    def test_is_first_run_with_sqlite_state(self):
        assert self.state.is_first_run() is True
        self.state.set_sqlite_mtime("cursor", "state.vscdb", 100.0)
        assert self.state.is_first_run() is False

    def test_is_first_run_no_state(self):
        assert self.state.is_first_run() is True


class TestExtractMetadataNewSources:
    """Path metadata extraction for cursor, codex, and openclaw."""

    def test_cursor_project_key_extracted(self):
        home = str(Path.home())
        path = f"{home}/.cursor/projects/my-project/agent-transcripts/abc.json"
        meta = _extract_metadata_from_path(path, "cursor")
        assert meta["project_key"] == "my-project"

    def test_cursor_no_project_key(self):
        home = str(Path.home())
        path = f"{home}/.cursor/ai-tracking/ai-code-tracking.db"
        meta = _extract_metadata_from_path(path, "cursor")
        assert "project_key" not in meta

    def test_codex_session_id_extracted(self):
        home = str(Path.home())
        path = f"{home}/.codex/sessions/session-abc123.jsonl"
        meta = _extract_metadata_from_path(path, "codex")
        assert meta["session_id"] == "session-abc123"

    def test_codex_history_no_session_id(self):
        home = str(Path.home())
        path = f"{home}/.codex/history.jsonl"
        meta = _extract_metadata_from_path(path, "codex")
        assert "session_id" not in meta

    def test_openclaw_session_id_extracted(self):
        home = str(Path.home())
        path = f"{home}/.openclaw/agents/main/sessions/sess-xyz.jsonl"
        meta = _extract_metadata_from_path(path, "openclaw")
        assert meta["session_id"] == "sess-xyz"

    def test_openclaw_sessions_json_no_id(self):
        home = str(Path.home())
        path = f"{home}/.openclaw/agents/main/sessions/sessions.json"
        meta = _extract_metadata_from_path(path, "openclaw")
        assert "session_id" not in meta


class TestScanSqliteDb:
    """Test SQLite database scanning."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path):
        self.tmp_path = tmp_path
        self.db_dir = tmp_path / "cursor" / "globalStorage"
        self.db_dir.mkdir(parents=True)
        self.db_path = str(self.db_dir / "state.vscdb")

        self.config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [
                {
                    "name": "cursor",
                    "enabled": True,
                    "globs": [],
                    "sqlite": [
                        {
                            "db_path": self.db_path,
                            "queries": [
                                {
                                    "file_type": "sqlite_composer",
                                    "sql": "SELECT key, value FROM composerData",
                                    "incremental_field": None,
                                },
                            ],
                        }
                    ],
                    "detect_path": str(self.db_dir),
                }
            ],
            "redact_patterns": [r"sk-[a-zA-Z0-9]{20,}"],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "state.json"):
            self.collector = LocalDataCollector(config=self.config, device_id="test-dev")
        # Mark startup as done so scans read data normally
        self.collector._startup_done = True

    def test_scan_sqlite_basic(self):
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("composerData:1", '{"text":"hello"}'), ("composerData:2", '{"text":"world"}')]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 2
        assert self.collector._buffer[0]["source"] == "cursor"
        assert self.collector._buffer[0]["file_type"] == "sqlite_composer"

    def test_scan_sqlite_incremental_with_param(self):
        db_path = str(self.db_dir / "tracking.db")
        _create_test_db(
            db_path, "ai_code_hashes", ["id", "createdAt"],
            [("1", "100"), ("2", "200"), ("3", "300")]
        )

        self.config["sources"][0]["sqlite"] = [{
            "db_path": db_path,
            "queries": [{
                "file_type": "sqlite_code_tracking",
                "sql": "SELECT id, createdAt FROM ai_code_hashes WHERE createdAt > ?",
                "incremental_field": "createdAt",
            }]
        }]
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state2.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        collector._startup_done = True

        collector._run_full_scan()
        assert len(collector._buffer) == 3  # All rows (last_value defaults to 0)

        # Second scan: should pick up only new rows
        db_key = os.path.basename(db_path)
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        assert st["incremental"]["sqlite_code_tracking"]["last_value"] == "300"

    def test_scan_sqlite_null_incremental(self):
        """Non-incremental queries re-scan all rows when mtime changes."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"data": 1}')]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        self.collector._buffer.clear()

        # Touch the db to update mtime
        time.sleep(0.05)
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO composerData VALUES (?, ?)", ("k2", '{"data": 2}'))
        conn.commit()
        conn.close()

        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 2  # Full re-scan

    def test_scan_sqlite_mtime_unchanged(self):
        """Non-incremental: skip if mtime unchanged."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"data": 1}')]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        self.collector._buffer.clear()

        # No mtime change → skipped
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0

    def test_scan_sqlite_db_missing(self):
        """Missing database path is silently skipped."""
        self.config["sources"][0]["sqlite"][0]["db_path"] = "/nonexistent/db.sqlite"
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()  # Should not raise
        assert len(collector._buffer) == 0

    def test_scan_sqlite_db_corrupted(self):
        """Corrupted database file logs warning and skips."""
        corrupt_path = str(self.db_dir / "corrupt.db")
        with open(corrupt_path, "wb") as f:
            f.write(b"this is not a sqlite database")

        self.config["sources"][0]["sqlite"][0]["db_path"] = corrupt_path
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()  # Should not raise
        assert len(collector._buffer) == 0

    def test_scan_sqlite_startup_seeds_only(self):
        """On startup, SQLite DBs are seeded (incremental values saved) but no rows buffered."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"data": 1}')]
        )

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "fresh.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        # First scan = startup, should seed only
        collector._run_full_scan()
        assert len(collector._buffer) == 0

    def test_scan_sqlite_redaction(self):
        """Secrets in SQLite rows get redacted."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"api_key": "sk-abcdefghijklmnopqrstuvwxyz"}')]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        raw = self.collector._buffer[0]["raw"]
        raw_str = json.dumps(raw)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in raw_str
        assert "[REDACTED]" in raw_str

    def test_scan_sqlite_dependency_order(self):
        """Queries with depends_on execute in correct order."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("composerData:1", '{"text":"hello"}')]
        )
        # Also create bubbleId table
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE bubbleData (key TEXT, value TEXT)")
        conn.execute("INSERT INTO bubbleData VALUES (?, ?)", ("bubbleId:1", '{"b":1}'))
        conn.commit()
        conn.close()

        self.config["sources"][0]["sqlite"][0]["queries"] = [
            {
                "file_type": "sqlite_bubble",
                "sql": "SELECT key, value FROM bubbleData",
                "incremental_field": None,
                "depends_on": "sqlite_composer",
            },
            {
                "file_type": "sqlite_composer",
                "sql": "SELECT key, value FROM composerData",
                "incremental_field": None,
            },
        ]
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "dep.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        collector._startup_done = True

        collector._run_full_scan()
        assert len(collector._buffer) == 2
        # Composer should be processed first
        assert collector._buffer[0]["file_type"] == "sqlite_composer"
        assert collector._buffer[1]["file_type"] == "sqlite_bubble"


class TestExecuteSqliteQuery:
    """Test envelope structure and edge cases for SQLite query execution."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path):
        self.tmp_path = tmp_path
        self.db_dir = tmp_path / "db"
        self.db_dir.mkdir()
        self.db_path = str(self.db_dir / "test.db")

        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": True,
                "globs": [],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "sqlite_test",
                        "sql": "SELECT key, value FROM test_table",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": str(self.db_dir),
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "state.json"):
            self.collector = LocalDataCollector(config=config, device_id="test-dev")
        self.collector._startup_done = True

    def test_envelope_structure_sqlite(self):
        _create_test_db(
            self.db_path, "test_table", ["key", "value"],
            [("k1", '{"msg":"hi"}')]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 1
        env = self.collector._buffer[0]

        assert "event_id" in env
        assert "timestamp" in env
        assert env["type"] == "local_session"
        assert env["device_id"] == "test-dev"
        assert env["source"] == "cursor"
        assert env["file_type"] == "sqlite_test"
        assert "raw" in env
        assert env["raw"]["key"] == "k1"
        # SQLite envelopes should NOT have these
        assert "project_key" not in env
        assert "session_id" not in env
        assert "line_number" not in env

    def test_oversized_row_skipped(self):
        big_value = "x" * (DEFAULT_MAX_EVENT_SIZE + 100)
        _create_test_db(
            self.db_path, "test_table", ["key", "value"],
            [("k1", big_value)]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0

    def test_empty_result_set(self):
        _create_test_db(self.db_path, "test_table", ["key", "value"], [])
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 0

    def test_incremental_value_tracking(self):
        db_path = str(self.db_dir / "inc.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "300"), ("c", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "inc.json"):
            collector = LocalDataCollector(config=config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()

        db_key = os.path.basename(db_path)
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        # Max of "100", "200", "300" (string comparison) = "300"
        assert st["incremental"]["items_q"]["last_value"] == "300"

    def test_corrupted_incremental_value_resets(self):
        """A saved incremental value that is a JSON object should be treated as
        corrupted and reset, allowing the query to re-scan."""
        db_path = str(self.db_dir / "corrupt.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "300"), ("c", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "corrupt.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # Inject a corrupted last_value (JSON object string, like what Cursor stored)
        db_key = os.path.basename(db_path)
        collector._scan_state.set_sqlite_incremental(
            "cursor", db_key, "items_q", '{"composerId":"abc","createdAt":100}'
        )
        collector._startup_done = True
        collector._run_full_scan()

        # All 3 rows should be captured (corruption was reset, query scanned from 0)
        assert len(collector._buffer) == 3
        # The last_value should now be a valid value ("300"), not the JSON blob
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        assert st["incremental"]["items_q"]["last_value"] == "300"

    def test_corrupted_incremental_value_json_array_resets(self):
        """A saved incremental value that is a JSON array also triggers reset."""
        db_path = str(self.db_dir / "corrupt_arr.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "corrupt_arr.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        db_key = os.path.basename(db_path)
        collector._scan_state.set_sqlite_incremental(
            "cursor", db_key, "items_q", '[{"row":"data"}]'
        )
        collector._startup_done = True
        collector._run_full_scan()

        assert len(collector._buffer) == 2
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        assert st["incremental"]["items_q"]["last_value"] == "200"

    def test_legitimate_string_incremental_value_preserved(self):
        """A legitimate string incremental value (not JSON object/array) is kept."""
        db_path = str(self.db_dir / "legit.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "300"), ("c", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "legit.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # Set a legitimate incremental value — should NOT be reset
        db_key = os.path.basename(db_path)
        collector._scan_state.set_sqlite_incremental(
            "cursor", db_key, "items_q", "200"
        )
        collector._startup_done = True
        collector._run_full_scan()

        # Only row with ts > "200" should be captured (ts="300")
        assert len(collector._buffer) == 1
        assert collector._buffer[0]["raw"]["ts"] == "300"

    def test_json_scalar_string_not_treated_as_corrupted(self):
        """A JSON scalar string like '"hello"' parses to str, not dict/list — preserved."""
        db_path = str(self.db_dir / "scalar.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "300")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "scalar.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # '"hello"' is valid JSON → parses to str "hello", NOT dict/list
        # So it should be preserved (not reset), proving the guard only catches
        # dict/list corruption, not arbitrary JSON scalars.
        db_key = os.path.basename(db_path)
        collector._scan_state.set_sqlite_incremental(
            "cursor", db_key, "items_q", '"hello"'
        )
        collector._startup_done = True
        collector._run_full_scan()

        # The value was preserved (not reset to None), so the query used
        # the preserved value. Both rows match since '"' < '1' in ASCII.
        assert len(collector._buffer) == 2
        # Verify the saved value was updated to "300" (max of returned rows)
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        assert st["incremental"]["items_q"]["last_value"] == "300"

    def test_numeric_string_incremental_value_not_affected_by_guard(self):
        """Numeric string values like '200' are NOT JSON objects — guard skips them."""
        db_path = str(self.db_dir / "numval.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "300"), ("c", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "numval.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # "200" is valid JSON (parses to int 200), but it's NOT dict/list
        # so the guard should leave it alone
        db_key = os.path.basename(db_path)
        collector._scan_state.set_sqlite_incremental(
            "cursor", db_key, "items_q", "200"
        )
        collector._startup_done = True
        collector._run_full_scan()

        # Only ts > "200" → "300" passes
        assert len(collector._buffer) == 1
        assert collector._buffer[0]["raw"]["ts"] == "300"

    def test_none_incremental_value_scans_from_beginning(self):
        """None saved value (fresh state) uses fallback 0 — scans everything."""
        db_path = str(self.db_dir / "fresh.db")
        _create_test_db(
            db_path, "items", ["id", "ts"],
            [("a", "100"), ("b", "200")]
        )

        config = self.collector._config.copy()
        config["sources"] = [{
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "sqlite": [{
                "db_path": db_path,
                "queries": [{
                    "file_type": "items_q",
                    "sql": "SELECT id, ts FROM items WHERE ts > ?",
                    "incremental_field": "ts",
                }]
            }],
            "detect_path": str(self.db_dir),
        }]

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "fresh.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # Don't set any incremental value — saved_inc_value is None
        collector._startup_done = True
        collector._run_full_scan()

        # All rows should be captured (WHERE ts > 0 matches all strings)
        assert len(collector._buffer) == 2

    def test_multiple_rows_buffered(self):
        _create_test_db(
            self.db_path, "test_table", ["key", "value"],
            [("k1", "v1"), ("k2", "v2"), ("k3", "v3")]
        )
        self.collector._run_full_scan()
        assert len(self.collector._buffer) == 3


class TestScanSourceWithSqlite:
    """Test _scan_source with both globs and sqlite configs."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.db_dir = tmp_path / "cursor"
        self.db_dir.mkdir()
        self.db_path = str(self.db_dir / "state.vscdb")
        self.jsonl_dir = tmp_path / "cursor" / "projects" / "myproj" / "agent-transcripts"
        self.jsonl_dir.mkdir(parents=True)

    def test_scan_source_globs_and_sqlite(self):
        # Create JSONL file
        jsonl_path = str(self.jsonl_dir / "transcript.json")
        with open(jsonl_path, "w") as f:
            f.write(json.dumps({"msg": "from_file"}))

        # Create SQLite DB
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"msg":"from_db"}')]
        )

        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": True,
                "globs": [{
                    "pattern": str(self.jsonl_dir / "*.json"),
                    "file_type": "agent_transcript",
                    "read_mode": "full",
                }],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "sqlite_composer",
                        "sql": "SELECT key, value FROM composerData",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": str(self.db_dir),
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()

        # Should have events from both file and SQLite
        file_types = [e["file_type"] for e in collector._buffer]
        assert "agent_transcript" in file_types
        assert "sqlite_composer" in file_types

    def test_scan_source_sqlite_only(self):
        _create_test_db(
            self.db_path, "data", ["id", "val"],
            [("1", "a")]
        )
        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": True,
                "globs": [],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "sqlite_data",
                        "sql": "SELECT id, val FROM data",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": str(self.db_dir),
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()
        assert len(collector._buffer) == 1

    def test_scan_source_disabled_skips_sqlite(self):
        _create_test_db(
            self.db_path, "data", ["id"], [("1",)]
        )
        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": False,
                "globs": [],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "x",
                        "sql": "SELECT id FROM data",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": str(self.db_dir),
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()
        assert len(collector._buffer) == 0

    def test_scan_source_detect_path_missing(self):
        """Missing detect_path skips entire source including sqlite."""
        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": True,
                "globs": [],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "x",
                        "sql": "SELECT 1",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": "/nonexistent/path",
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "s.json"):
            collector = LocalDataCollector(config=config, device_id="dev")
        collector._startup_done = True
        collector._run_full_scan()
        assert len(collector._buffer) == 0


class TestExtractMetadataAntigravity:
    """Path metadata extraction for antigravity (Gemini desktop IDE)."""

    def test_brain_artifact_session_id(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/brain/550e8400-e29b-41d4-a716-446655440000/notes.md"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_brain_metadata_session_id(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/brain/abc-def-123/notes.metadata.json"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "abc-def-123"

    def test_conversation_session_id(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/conversations/conv-uuid-456.pb"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "conv-uuid-456"

    def test_annotation_session_id(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/annotations/anno-uuid-789.pbtxt"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "anno-uuid-789"

    def test_no_session_id_for_unknown_subdir(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/other/something.txt"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert "session_id" not in meta

    def test_no_session_id_for_dotfile(self):
        """Dotfile names like '.' or '..' should not be used as session_id."""
        home = str(Path.home())
        # brain with a very short/invalid directory name
        path = f"{home}/.gemini/antigravity/brain/ab/file.md"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert "session_id" not in meta  # "ab" is < 3 chars

    def test_brain_is_last_segment_no_child(self):
        """If 'brain' is the last path segment, no session_id is extracted."""
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/brain"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert "session_id" not in meta

    def test_conversation_multi_dot_filename(self):
        """Conversation file with multiple dots uses stem (everything before last dot)."""
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/conversations/sess.backup.pb"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "sess.backup"

    def test_conversation_hidden_file_rejected(self):
        """Hidden file (.pb) in conversations/ has stem '.pb' which starts with dot."""
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/conversations/.pb"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert "session_id" not in meta

    def test_brain_appears_twice_in_path(self):
        """If 'brain' appears multiple times, first occurrence is used."""
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/brain/uuid-abc-123/brain/nested.md"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["session_id"] == "uuid-abc-123"

    def test_source_file_tilde_collapsed(self):
        home = str(Path.home())
        path = f"{home}/.gemini/antigravity/brain/uuid123/file.md"
        meta = _extract_metadata_from_path(path, "antigravity")
        assert meta["source_file"] == "~/.gemini/antigravity/brain/uuid123/file.md"


class TestContentType:
    """Tests for content_type support in _read_full_file."""

    @pytest.fixture(autouse=True)
    def setup_collector(self, tmp_path):
        self.tmp_path = tmp_path
        self.data_dir = tmp_path / "data"
        self.data_dir.mkdir(parents=True)

        config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [],
            "redact_patterns": [],
            "skip_files": [],
        }
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "s.json"):
            self.collector = LocalDataCollector(config=config, device_id="dev")

    def test_content_type_json_default(self):
        """Default content_type='json' works like before — raw JSON passed through."""
        fp = str(self.data_dir / "data.json")
        with open(fp, "w") as f:
            json.dump({"key": "value"}, f)

        self.collector._read_full_file("test_src", fp, "test_type")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"] == {"key": "value"}

    def test_content_type_json_explicit(self):
        """Explicit content_type='json' behaves the same as default."""
        fp = str(self.data_dir / "data2.json")
        with open(fp, "w") as f:
            json.dump({"hello": "world"}, f)

        self.collector._read_full_file("test_src", fp, "test_type", content_type="json")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"] == {"hello": "world"}

    def test_content_type_text(self):
        """content_type='text' wraps file content as {"content": text}."""
        fp = str(self.data_dir / "notes.md")
        with open(fp, "w") as f:
            f.write("# Hello\n\nThis is markdown content.")

        self.collector._read_full_file("test_src", fp, "brain_artifact", content_type="text")
        assert len(self.collector._buffer) == 1
        raw = self.collector._buffer[0]["raw"]
        assert raw["content"] == "# Hello\n\nThis is markdown content."

    def test_content_type_text_preserves_whitespace(self):
        """Text content preserves internal whitespace and newlines."""
        fp = str(self.data_dir / "doc.txt")
        with open(fp, "w") as f:
            f.write("line1\n  indented\n\nline4\n")

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 1
        raw = self.collector._buffer[0]["raw"]
        assert "line1\n  indented\n\nline4\n" == raw["content"]

    def test_content_type_binary(self):
        """content_type='binary' wraps file content as {"content_base64": ...}."""
        import base64
        fp = str(self.data_dir / "conv.pb")
        binary_data = b"\x08\x01\x12\x05hello\x1a\x03\x00\xff\xfe"
        with open(fp, "wb") as f:
            f.write(binary_data)

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 1
        raw = self.collector._buffer[0]["raw"]
        assert "content_base64" in raw
        decoded = base64.b64decode(raw["content_base64"])
        assert decoded == binary_data

    def test_content_type_binary_empty_file(self):
        """Empty binary file is skipped."""
        fp = str(self.data_dir / "empty.pb")
        with open(fp, "wb") as f:
            pass  # empty

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 0

    def test_content_type_text_empty_file(self):
        """Empty text file is skipped."""
        fp = str(self.data_dir / "empty.md")
        with open(fp, "w") as f:
            f.write("   ")

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 0

    def test_content_type_text_envelope_fields(self):
        """Text content envelope has correct source, file_type, and type."""
        fp = str(self.data_dir / "note.md")
        with open(fp, "w") as f:
            f.write("content here")

        self.collector._read_full_file("antigravity", fp, "brain_artifact", content_type="text")
        assert len(self.collector._buffer) == 1
        env = self.collector._buffer[0]
        assert env["source"] == "antigravity"
        assert env["file_type"] == "brain_artifact"
        assert env["type"] == "local_session"

    def test_scan_glob_passes_content_type(self):
        """_scan_glob passes content_type from config to _read_full_file."""
        md_file = self.data_dir / "test.md"
        md_file.write_text("# Test markdown")

        glob_config = {
            "pattern": str(self.data_dir / "*.md"),
            "file_type": "brain_artifact",
            "read_mode": "full",
            "content_type": "text",
        }
        self.collector._startup_done = True
        self.collector._scan_glob("antigravity", glob_config, is_startup=False)
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["content"] == "# Test markdown"

    def test_scan_glob_default_content_type_is_json(self):
        """_scan_glob defaults to content_type='json' when not specified."""
        json_file = self.data_dir / "meta.json"
        json_file.write_text(json.dumps({"meta": True}))

        glob_config = {
            "pattern": str(self.data_dir / "*.json"),
            "file_type": "brain_metadata",
            "read_mode": "full",
            # no content_type — should default to "json"
        }
        self.collector._startup_done = True
        self.collector._scan_glob("antigravity", glob_config, is_startup=False)
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"] == {"meta": True}

    def test_invalid_content_type_falls_back_to_json(self):
        """An invalid content_type falls back to 'json' with a warning."""
        fp = str(self.data_dir / "data.json")
        with open(fp, "w") as f:
            json.dump({"ok": True}, f)

        self.collector._read_full_file("test_src", fp, "test_type", content_type="xml")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"] == {"ok": True}

    def test_oversized_binary_file_skipped(self):
        """Binary files exceeding max_event_size are skipped before reading."""
        fp = str(self.data_dir / "huge.pb")
        with open(fp, "wb") as f:
            f.write(b"\x00" * (1_048_576 + 1))

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 0

    def test_oversized_text_file_skipped(self):
        """Text files exceeding max_event_size are skipped before reading."""
        fp = str(self.data_dir / "huge.md")
        with open(fp, "w") as f:
            f.write("x" * (1_048_576 + 1))

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 0

    def test_oversized_file_records_mtime(self):
        """Oversized files record mtime so they aren't re-checked every cycle."""
        fp = str(self.data_dir / "big.pb")
        with open(fp, "wb") as f:
            f.write(b"\x00" * (1_048_576 + 1))

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 0

        # Call again — should be skipped by mtime check, not re-read
        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 0
        # Verify state was recorded
        state = self.collector._scan_state.get_file_state("test_src", fp)
        assert state["mtime"] == os.stat(fp).st_mtime

    def test_empty_binary_file_records_mtime(self):
        """Empty binary files record mtime to avoid re-checking every cycle."""
        fp = str(self.data_dir / "zero.pb")
        with open(fp, "wb") as f:
            pass

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 0
        state = self.collector._scan_state.get_file_state("test_src", fp)
        assert state["mtime"] == os.stat(fp).st_mtime

    def test_empty_text_file_records_mtime(self):
        """Empty/whitespace text files record mtime to avoid re-checking every cycle."""
        fp = str(self.data_dir / "blank.md")
        with open(fp, "w") as f:
            f.write("   \n\n  ")

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 0
        state = self.collector._scan_state.get_file_state("test_src", fp)
        assert state["mtime"] == os.stat(fp).st_mtime

    def test_same_mtime_skips_reread(self):
        """File with unchanged mtime is not re-read (dedup)."""
        fp = str(self.data_dir / "stable.json")
        with open(fp, "w") as f:
            json.dump({"v": 1}, f)

        self.collector._read_full_file("test_src", fp, "test_type")
        assert len(self.collector._buffer) == 1

        # Second call — same mtime → skipped
        self.collector._read_full_file("test_src", fp, "test_type")
        assert len(self.collector._buffer) == 1  # still 1, not 2

    def test_updated_mtime_triggers_reread(self):
        """File with changed mtime is re-read."""
        fp = str(self.data_dir / "changing.json")
        with open(fp, "w") as f:
            json.dump({"v": 1}, f)

        self.collector._read_full_file("test_src", fp, "test_type")
        assert len(self.collector._buffer) == 1

        # Touch the file to update mtime
        import time
        time.sleep(0.05)
        with open(fp, "w") as f:
            json.dump({"v": 2}, f)

        self.collector._read_full_file("test_src", fp, "test_type")
        assert len(self.collector._buffer) == 2
        assert self.collector._buffer[1]["raw"] == {"v": 2}

    def test_invalid_json_with_json_content_type_skipped(self):
        """Invalid JSON files are gracefully skipped (no crash)."""
        fp = str(self.data_dir / "bad.json")
        with open(fp, "w") as f:
            f.write("{invalid json content")

        self.collector._read_full_file("test_src", fp, "test_type", content_type="json")
        assert len(self.collector._buffer) == 0

    def test_text_with_unicode_and_special_chars(self):
        """Text with unicode, newlines, quotes, and backslashes is properly wrapped."""
        fp = str(self.data_dir / "unicode.md")
        content = 'Line with "quotes" and \\backslash\nUnicode: \u00e9\u00e8\u00ea \U0001f600\nTab:\there'
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["content"] == content

    def test_text_only_newlines_is_empty(self):
        """File containing only newlines is treated as empty."""
        fp = str(self.data_dir / "newlines.md")
        with open(fp, "w") as f:
            f.write("\n\n\n")

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 0

    def test_binary_with_null_bytes(self):
        """Binary files with null bytes are correctly base64-encoded."""
        import base64
        fp = str(self.data_dir / "nulls.pb")
        data = b"\x00" * 100 + b"\xff" * 100
        with open(fp, "wb") as f:
            f.write(data)

        self.collector._read_full_file("test_src", fp, "conversation", content_type="binary")
        assert len(self.collector._buffer) == 1
        decoded = base64.b64decode(self.collector._buffer[0]["raw"]["content_base64"])
        assert decoded == data

    def test_content_type_empty_string_falls_back(self):
        """Empty string content_type falls back to json."""
        fp = str(self.data_dir / "fallback.json")
        with open(fp, "w") as f:
            json.dump({"ok": True}, f)

        self.collector._read_full_file("test_src", fp, "test_type", content_type="")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"] == {"ok": True}

    def test_text_preserves_leading_trailing_whitespace(self):
        """Text mode preserves leading/trailing whitespace (no stripping)."""
        fp = str(self.data_dir / "padded.md")
        content = "  leading and trailing spaces  "
        with open(fp, "w") as f:
            f.write(content)

        self.collector._read_full_file("test_src", fp, "doc", content_type="text")
        assert len(self.collector._buffer) == 1
        assert self.collector._buffer[0]["raw"]["content"] == content


class TestWatcherSqlite:
    """Test watcher integration for SQLite database files."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.db_dir = tmp_path / "cursor" / "globalStorage"
        self.db_dir.mkdir(parents=True)
        self.db_path = str(self.db_dir / "state.vscdb")

        self.config = {
            "enabled": True,
            "scan_interval_seconds": 60,
            "upload_endpoint": "https://api.oximy.com/api/v1/ingest/local-sessions",
            "max_events_per_batch": 200,
            "backfill_max_age_days": 7,
            "sources": [{
                "name": "cursor",
                "enabled": True,
                "globs": [],
                "sqlite": [{
                    "db_path": self.db_path,
                    "queries": [{
                        "file_type": "sqlite_test",
                        "sql": "SELECT key, value FROM data",
                        "incremental_field": None,
                    }]
                }],
                "detect_path": str(self.db_dir),
            }],
            "redact_patterns": [],
            "skip_files": [],
        }

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "s.json"):
            self.collector = LocalDataCollector(config=self.config, device_id="dev")
        self.collector._startup_done = True

    def test_is_watched_sqlite_db_true(self):
        assert self.collector._is_watched_sqlite_db(self.db_path) is True

    def test_is_watched_sqlite_db_false(self):
        assert self.collector._is_watched_sqlite_db("/random/other.db") is False

    def test_get_watch_paths_includes_sqlite_dirs(self):
        paths = self.collector._get_watch_paths()
        # Should include detect_path AND sqlite db parent dir
        assert str(self.db_dir) in paths
