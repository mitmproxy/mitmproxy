"""Tests for the proactive playbook suggestion writer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mitmproxy.addons.oximy.playbooks import clear_suggestion
from mitmproxy.addons.oximy.playbooks import read_suggestion_feedback
from mitmproxy.addons.oximy.playbooks import record_suggestion_feedback
from mitmproxy.addons.oximy.playbooks import reset_suggestion_state
from mitmproxy.addons.oximy.playbooks import should_write_suggestion
from mitmproxy.addons.oximy.playbooks import write_suggestion_from_server

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset cooldown state before every test."""
    reset_suggestion_state()
    yield
    reset_suggestion_state()


@pytest.fixture
def sample_suggestion() -> dict:
    """Typical server-provided suggestion payload."""
    return {
        "id": "sug-abc123",
        "playbookId": "pb-456",
        "playbookName": "Code Review Checklist",
        "playbookDescription": "A checklist for thorough code reviews",
        "playbookCategory": "coding",
        "promptTemplate": "Review this code for {{focus_area}}",
        "confidence": 0.92,
    }


@pytest.fixture
def mock_oximy_dir(tmp_path: Path, monkeypatch):
    """Redirect OXIMY_DIR, SUGGESTIONS_FILE, and SUGGESTION_STATE_FILE to tmp_path."""
    oximy_dir = tmp_path / ".oximy"
    suggestions_file = oximy_dir / "suggestions.json"
    state_file = oximy_dir / "suggestion-state.json"
    monkeypatch.setattr(
        "mitmproxy.addons.oximy.playbooks.OXIMY_DIR", oximy_dir
    )
    monkeypatch.setattr(
        "mitmproxy.addons.oximy.playbooks.SUGGESTIONS_FILE", suggestions_file
    )
    monkeypatch.setattr(
        "mitmproxy.addons.oximy.playbooks.SUGGESTION_STATE_FILE", state_file
    )
    return oximy_dir, suggestions_file, state_file


# =============================================================================
# write_suggestion_from_server
# =============================================================================


class TestWriteSuggestionFromServer:
    def test_creates_suggestions_file(self, mock_oximy_dir, sample_suggestion):
        """Should create suggestions.json with the correct shape."""
        _, suggestions_file, _ = mock_oximy_dir

        write_suggestion_from_server(sample_suggestion)

        assert suggestions_file.exists()
        data = json.loads(suggestions_file.read_text())
        assert data["id"] == "sug-abc123"
        assert data["playbook"]["id"] == "pb-456"
        assert data["playbook"]["name"] == "Code Review Checklist"
        assert data["playbook"]["description"] == "A checklist for thorough code reviews"
        assert data["playbook"]["category"] == "coding"
        assert data["playbook"]["promptTemplate"] == "Review this code for {{focus_area}}"
        assert data["confidence"] == 0.92
        assert data["status"] == "pending"
        assert "createdAt" in data

    def test_creates_oximy_dir_if_missing(self, mock_oximy_dir, sample_suggestion):
        """Should create the ~/.oximy directory if it doesn't exist."""
        oximy_dir, _, _ = mock_oximy_dir
        assert not oximy_dir.exists()

        write_suggestion_from_server(sample_suggestion)

        assert oximy_dir.exists()

    def test_handles_missing_fields(self, mock_oximy_dir):
        """Should use empty defaults for missing suggestion fields."""
        _, suggestions_file, _ = mock_oximy_dir

        write_suggestion_from_server({"id": "minimal"})

        data = json.loads(suggestions_file.read_text())
        assert data["id"] == "minimal"
        assert data["playbook"]["id"] == ""
        assert data["playbook"]["name"] == ""
        assert data["confidence"] == 0

    def test_overwrites_existing(self, mock_oximy_dir, sample_suggestion):
        """Should overwrite an existing suggestions.json."""
        _, suggestions_file, _ = mock_oximy_dir

        write_suggestion_from_server({"id": "old"})
        write_suggestion_from_server(sample_suggestion)

        data = json.loads(suggestions_file.read_text())
        assert data["id"] == "sug-abc123"

    def test_handles_io_error_gracefully(self, mock_oximy_dir, sample_suggestion, caplog):
        """Should catch and log IO errors without raising."""
        _, suggestions_file, _ = mock_oximy_dir

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should not raise
            write_suggestion_from_server(sample_suggestion)

        assert "Failed to write suggestion" in caplog.text

    def test_updates_last_suggestion_id(self, mock_oximy_dir, sample_suggestion):
        """Writing a suggestion should update _last_suggestion_id for dedup."""
        write_suggestion_from_server(sample_suggestion)

        # Same ID should now be deduplicated
        assert not should_write_suggestion("sug-abc123")
        # Different ID should pass
        assert should_write_suggestion("sug-different")


# =============================================================================
# read_suggestion_feedback
# =============================================================================


class TestReadSuggestionFeedback:
    def test_returns_none_if_file_missing(self, mock_oximy_dir):
        """Should return None when suggestions.json doesn't exist."""
        assert read_suggestion_feedback() is None

    def test_returns_none_if_status_pending(self, mock_oximy_dir):
        """Should return None if user hasn't interacted (status=pending)."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text(json.dumps({"status": "pending"}))

        assert read_suggestion_feedback() is None

    def test_returns_data_if_used(self, mock_oximy_dir):
        """Should return the full dict when status='used'."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": "sug-1", "status": "used", "playbook": {"id": "pb-1"}}
        suggestions_file.write_text(json.dumps(payload))

        result = read_suggestion_feedback()
        assert result is not None
        assert result["status"] == "used"
        assert result["id"] == "sug-1"

    def test_returns_data_if_dismissed(self, mock_oximy_dir):
        """Should return the full dict when status='dismissed'."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": "sug-2", "status": "dismissed"}
        suggestions_file.write_text(json.dumps(payload))

        result = read_suggestion_feedback()
        assert result is not None
        assert result["status"] == "dismissed"

    def test_returns_none_on_invalid_json(self, mock_oximy_dir):
        """Should return None if file contains invalid JSON."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text("not valid json{{{")

        assert read_suggestion_feedback() is None

    def test_returns_none_on_empty_status(self, mock_oximy_dir):
        """Should return None if status field is missing or empty."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text(json.dumps({"id": "sug-3"}))

        assert read_suggestion_feedback() is None


# =============================================================================
# clear_suggestion
# =============================================================================


class TestClearSuggestion:
    def test_deletes_file(self, mock_oximy_dir):
        """Should delete suggestions.json if it exists."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text("{}")

        clear_suggestion()

        assert not suggestions_file.exists()

    def test_handles_missing_file(self, mock_oximy_dir):
        """Should not raise if file doesn't exist."""
        # Should not raise
        clear_suggestion()

    def test_handles_permission_error(self, mock_oximy_dir, caplog):
        """Should catch and log errors without raising."""
        _, suggestions_file, _ = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text("{}")

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            clear_suggestion()

        assert "Failed to clear suggestion file" in caplog.text


# =============================================================================
# should_write_suggestion (cooldown + dedup gating)
# =============================================================================


class TestShouldWriteSuggestion:
    def test_allows_when_no_cooldown(self, mock_oximy_dir):
        """Should allow suggestion when there's no active cooldown."""
        assert should_write_suggestion("sug-new") is True

    def test_blocks_during_cooldown(self, mock_oximy_dir):
        """Should block suggestions while cooldown is active."""
        record_suggestion_feedback("used", cooldown_minutes=10)

        assert should_write_suggestion("sug-new") is False

    def test_allows_after_cooldown_expires(self, mock_oximy_dir):
        """Should allow suggestions after cooldown period expires."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            # Record feedback at t=1000
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("used", cooldown_minutes=5)

            # Still in cooldown at t=1100 (100s < 300s)
            mock_time.time.return_value = 1100.0
            assert should_write_suggestion("sug-new") is False

            # Past cooldown at t=1400 (400s > 300s)
            mock_time.time.return_value = 1400.0
            assert should_write_suggestion("sug-new") is True

    def test_blocks_duplicate_id(self, mock_oximy_dir, sample_suggestion):
        """Should block writing the same suggestion ID twice (dedup)."""
        write_suggestion_from_server(sample_suggestion)

        assert should_write_suggestion("sug-abc123") is False

    def test_allows_different_id(self, mock_oximy_dir, sample_suggestion):
        """Should allow a different suggestion ID after writing one."""
        write_suggestion_from_server(sample_suggestion)

        assert should_write_suggestion("sug-different") is True

    def test_loads_state_from_corrupt_file(self, mock_oximy_dir):
        """Should gracefully handle corrupt state file."""
        _, _, state_file = mock_oximy_dir
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not valid json{{{")

        # Should not raise, and should allow suggestions
        assert should_write_suggestion("sug-new") is True

    def test_loads_state_from_missing_file(self, mock_oximy_dir):
        """Should work fine when state file doesn't exist."""
        assert should_write_suggestion("sug-new") is True


# =============================================================================
# record_suggestion_feedback (cooldown start)
# =============================================================================


class TestRecordSuggestionFeedback:
    def test_used_starts_default_5min_cooldown(self, mock_oximy_dir):
        """'used' action should start a 5-minute cooldown by default."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("used")

            # At t=1200 (200s < 300s) should be blocked
            mock_time.time.return_value = 1200.0
            assert should_write_suggestion("sug-new") is False

            # At t=1400 (400s > 300s) should be allowed
            mock_time.time.return_value = 1400.0
            assert should_write_suggestion("sug-new") is True

    def test_dismissed_starts_default_24h_cooldown(self, mock_oximy_dir):
        """'dismissed' action should start a 24-hour cooldown by default."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("dismissed")

            # At t=1000 + 23h (82800s) should be blocked
            mock_time.time.return_value = 1000.0 + 82800
            assert should_write_suggestion("sug-new") is False

            # At t=1000 + 25h (90000s) should be allowed
            mock_time.time.return_value = 1000.0 + 90000
            assert should_write_suggestion("sug-new") is True

    def test_custom_cooldown_values(self, mock_oximy_dir):
        """Should respect custom cooldown values from the API."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("used", cooldown_minutes=10)

            # At t=1500 (500s < 600s) should be blocked
            mock_time.time.return_value = 1500.0
            assert should_write_suggestion("sug-new") is False

            # At t=1700 (700s > 600s) should be allowed
            mock_time.time.return_value = 1700.0
            assert should_write_suggestion("sug-new") is True

    def test_custom_dismissal_cooldown(self, mock_oximy_dir):
        """Should respect custom dismissal cooldown hours."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("dismissed", dismissal_cooldown_hours=2)

            # At t=1000 + 1h (3600s) should be blocked
            mock_time.time.return_value = 1000.0 + 3600
            assert should_write_suggestion("sug-new") is False

            # At t=1000 + 3h (10800s) should be allowed
            mock_time.time.return_value = 1000.0 + 10800
            assert should_write_suggestion("sug-new") is True

    def test_zero_cooldown_from_api(self, mock_oximy_dir):
        """Cooldown of 0 should effectively mean no cooldown."""
        record_suggestion_feedback("used", cooldown_minutes=0)

        assert should_write_suggestion("sug-new") is True

    def test_writes_state_file(self, mock_oximy_dir):
        """Should persist state to disk."""
        _, _, state_file = mock_oximy_dir

        record_suggestion_feedback("dismissed")

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "cooldownUntil" in data
        assert data["lastAction"] == "dismissed"
        assert "lastActionAt" in data

    def test_state_survives_reload(self, mock_oximy_dir):
        """State file should preserve cooldown across reset (simulating restart)."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0
            record_suggestion_feedback("used", cooldown_minutes=10)

            # Simulate restart: reset in-memory state
            reset_suggestion_state()

            # Still in cooldown at t=1200 after reload
            mock_time.time.return_value = 1200.0
            assert should_write_suggestion("sug-new") is False


# =============================================================================
# Full cycle integration
# =============================================================================


class TestFullCycle:
    def test_write_dismiss_cooldown_expire_new_suggestion(self, mock_oximy_dir):
        """Full lifecycle: write -> dismiss -> cooldown -> expire -> new suggestion."""
        with patch("mitmproxy.addons.oximy.playbooks.time") as mock_time:
            mock_time.time.return_value = 1000.0

            # 1. Write initial suggestion
            assert should_write_suggestion("sug-1") is True
            write_suggestion_from_server({"id": "sug-1", "playbookName": "Test"})

            # 2. Same suggestion should be deduplicated
            assert should_write_suggestion("sug-1") is False

            # 3. Dismiss triggers cooldown (2h for easier testing)
            record_suggestion_feedback("dismissed", dismissal_cooldown_hours=2)

            # 4. New suggestion blocked during cooldown
            mock_time.time.return_value = 1000.0 + 3600  # +1h
            assert should_write_suggestion("sug-2") is False

            # 5. Cooldown expires
            mock_time.time.return_value = 1000.0 + 8000  # +2.2h
            assert should_write_suggestion("sug-2") is True

            # 6. Write new suggestion succeeds
            write_suggestion_from_server({"id": "sug-2", "playbookName": "New"})
            assert should_write_suggestion("sug-2") is False  # deduped
            assert should_write_suggestion("sug-3") is True   # different ID ok
