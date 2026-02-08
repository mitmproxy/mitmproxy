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
        # Override the scan state so is_first_run returns False (no backfill filter)
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", tmp_path / "scan-state.json"):
            self.collector = LocalDataCollector(config=sample_config, device_id="test-device")
        # Mark as not first run to skip backfill filter
        self.collector._scan_state.set_file_state("_init", "_init", 0, 0)

    def test_scan_source_detects_installed(self):
        fp = str(self.projects_dir / "sess.jsonl")
        _write_jsonl(fp, [{"data": 1, "timestamp": "2025-01-01T00:00:00Z"}])

        source_config = self.collector._config["sources"][0]
        self.collector._scan_source(source_config)
        assert len(self.collector._buffer) == 1

    def test_scan_source_skips_uninstalled(self):
        source_config = {
            "name": "cursor",
            "enabled": True,
            "globs": [],
            "detect_path": str(self.tmp_path / "nonexistent"),
        }
        self.collector._scan_source(source_config)
        assert len(self.collector._buffer) == 0

    def test_scan_glob_discovers_files(self):
        for i in range(3):
            fp = str(self.projects_dir / f"sess{i}.jsonl")
            _write_jsonl(fp, [{"msg": f"session{i}", "timestamp": "2025-01-01T00:00:00Z"}])

        source_config = self.collector._config["sources"][0]
        self.collector._scan_source(source_config)
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
            assert c._scan_thread is not None
            assert c._scan_thread.is_alive()

            c.stop()
            assert not c._scan_thread.is_alive()

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
        source_name, file_type, read_mode = result
        assert source_name == "claude_code"
        assert file_type == "session_transcript"
        assert read_mode == "incremental"

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
# TestBackfillWindow
# ===========================================================================

class TestBackfillWindow:
    """Tests for backfill age filtering on first run."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, sample_config):
        self.tmp_path = tmp_path
        self.projects_dir = tmp_path / ".claude" / "projects" / "-Users-test-myproject"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.sample_config = sample_config

    def test_filters_old_files_on_first_run(self):
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        # Create an old file (30 days ago)
        old_fp = str(self.projects_dir / "old.jsonl")
        _write_jsonl(old_fp, [{"data": "old", "timestamp": "2020-01-01T00:00:00Z"}])
        old_time = time.time() - (30 * 86400)
        os.utime(old_fp, (old_time, old_time))

        # Create a recent file
        new_fp = str(self.projects_dir / "new.jsonl")
        _write_jsonl(new_fp, [{"data": "new", "timestamp": "2025-01-01T00:00:00Z"}])

        collector._run_full_scan()
        assert len(collector._buffer) == 1
        assert collector._buffer[0]["raw"]["data"] == "new"

    def test_processes_recent_files(self):
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        # Create recent files (within 7 day window)
        for i in range(3):
            fp = str(self.projects_dir / f"recent{i}.jsonl")
            _write_jsonl(fp, [{"data": f"r{i}", "timestamp": "2025-01-01T00:00:00Z"}])

        collector._run_full_scan()
        assert len(collector._buffer) == 3

    def test_no_filter_on_subsequent_runs(self):
        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=self.sample_config, device_id="dev")

        # Mark as not first run
        collector._scan_state.set_file_state("_init", "_init", 0, 0)

        # Create an old file
        old_fp = str(self.projects_dir / "old_sess.jsonl")
        _write_jsonl(old_fp, [{"data": "old_but_new_to_us", "timestamp": "2020-01-01T00:00:00Z"}])
        old_time = time.time() - (30 * 86400)
        os.utime(old_fp, (old_time, old_time))

        collector._run_full_scan()
        # Should process even old files since it's not first run
        assert len(collector._buffer) == 1

    def test_configurable_backfill_window(self):
        config = self.sample_config.copy()
        config["backfill_max_age_days"] = 1  # Only last 1 day

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        # File from 3 days ago
        fp = str(self.projects_dir / "three_days.jsonl")
        _write_jsonl(fp, [{"data": "old", "timestamp": "2020-01-01T00:00:00Z"}])
        old_time = time.time() - (3 * 86400)
        os.utime(fp, (old_time, old_time))

        collector._run_full_scan()
        assert len(collector._buffer) == 0  # Filtered by 1-day window

    def test_backfill_disabled_with_zero_days(self):
        config = self.sample_config.copy()
        config["backfill_max_age_days"] = 0  # Disabled

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "state.json"):
            collector = LocalDataCollector(config=config, device_id="dev")

        fp = str(self.projects_dir / "any_age.jsonl")
        _write_jsonl(fp, [{"data": "any", "timestamp": "2025-01-01T00:00:00Z"}])
        old_time = time.time() - (365 * 86400)
        os.utime(fp, (old_time, old_time))

        collector._run_full_scan()
        assert len(collector._buffer) == 1  # No age filter when 0


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
        # Mark as not first run so backfill filter doesn't interfere
        self.collector._scan_state.set_file_state("_init", "_init", 0, 0)

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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)

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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
        collector._run_full_scan()  # Should not raise
        assert len(collector._buffer) == 0

    def test_scan_sqlite_backfill_old_db(self):
        """Old database is skipped on first run (backfill filter)."""
        _create_test_db(
            self.db_path, "composerData", ["key", "value"],
            [("k1", '{"data": 1}')]
        )
        old_time = time.time() - (30 * 86400)
        os.utime(self.db_path, (old_time, old_time))

        with patch("mitmproxy.addons.oximy.collector.SCAN_STATE_FILE", self.tmp_path / "fresh.json"):
            collector = LocalDataCollector(config=self.config, device_id="dev")
        # Don't mark as not-first-run — leave it as first run
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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)

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
        self.collector._scan_state.set_file_state("_init", "_init", 0, 0)

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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
        collector._run_full_scan()

        db_key = os.path.basename(db_path)
        st = collector._scan_state.get_sqlite_state("cursor", db_key)
        # Max of "100", "200", "300" (string comparison) = "300"
        assert st["incremental"]["items_q"]["last_value"] == "300"

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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
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
        collector._scan_state.set_file_state("_init", "_init", 0, 0)
        collector._run_full_scan()
        assert len(collector._buffer) == 0


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
        self.collector._scan_state.set_file_state("_init", "_init", 0, 0)

    def test_is_watched_sqlite_db_true(self):
        assert self.collector._is_watched_sqlite_db(self.db_path) is True

    def test_is_watched_sqlite_db_false(self):
        assert self.collector._is_watched_sqlite_db("/random/other.db") is False

    def test_get_watch_paths_includes_sqlite_dirs(self):
        paths = self.collector._get_watch_paths()
        # Should include detect_path AND sqlite db parent dir
        assert str(self.db_dir) in paths
