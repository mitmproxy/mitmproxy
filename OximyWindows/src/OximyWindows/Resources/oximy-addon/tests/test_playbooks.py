"""Tests for the proactive playbook suggestion writer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mitmproxy.addons.oximy.playbooks import clear_suggestion
from mitmproxy.addons.oximy.playbooks import read_suggestion_feedback
from mitmproxy.addons.oximy.playbooks import write_suggestion_from_server

# =============================================================================
# Fixtures
# =============================================================================


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
    """Redirect OXIMY_DIR and SUGGESTIONS_FILE to tmp_path."""
    oximy_dir = tmp_path / ".oximy"
    suggestions_file = oximy_dir / "suggestions.json"
    monkeypatch.setattr(
        "mitmproxy.addons.oximy.playbooks.OXIMY_DIR", oximy_dir
    )
    monkeypatch.setattr(
        "mitmproxy.addons.oximy.playbooks.SUGGESTIONS_FILE", suggestions_file
    )
    return oximy_dir, suggestions_file


# =============================================================================
# write_suggestion_from_server
# =============================================================================


class TestWriteSuggestionFromServer:
    def test_creates_suggestions_file(self, mock_oximy_dir, sample_suggestion):
        """Should create suggestions.json with the correct shape."""
        _, suggestions_file = mock_oximy_dir

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
        oximy_dir, _ = mock_oximy_dir
        assert not oximy_dir.exists()

        write_suggestion_from_server(sample_suggestion)

        assert oximy_dir.exists()

    def test_handles_missing_fields(self, mock_oximy_dir):
        """Should use empty defaults for missing suggestion fields."""
        _, suggestions_file = mock_oximy_dir

        write_suggestion_from_server({"id": "minimal"})

        data = json.loads(suggestions_file.read_text())
        assert data["id"] == "minimal"
        assert data["playbook"]["id"] == ""
        assert data["playbook"]["name"] == ""
        assert data["confidence"] == 0

    def test_overwrites_existing(self, mock_oximy_dir, sample_suggestion):
        """Should overwrite an existing suggestions.json."""
        _, suggestions_file = mock_oximy_dir

        write_suggestion_from_server({"id": "old"})
        write_suggestion_from_server(sample_suggestion)

        data = json.loads(suggestions_file.read_text())
        assert data["id"] == "sug-abc123"

    def test_handles_io_error_gracefully(self, mock_oximy_dir, sample_suggestion, caplog):
        """Should catch and log IO errors without raising."""
        _, suggestions_file = mock_oximy_dir

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should not raise
            write_suggestion_from_server(sample_suggestion)

        assert "Failed to write suggestion" in caplog.text


# =============================================================================
# read_suggestion_feedback
# =============================================================================


class TestReadSuggestionFeedback:
    def test_returns_none_if_file_missing(self, mock_oximy_dir):
        """Should return None when suggestions.json doesn't exist."""
        assert read_suggestion_feedback() is None

    def test_returns_none_if_status_pending(self, mock_oximy_dir):
        """Should return None if user hasn't interacted (status=pending)."""
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text(json.dumps({"status": "pending"}))

        assert read_suggestion_feedback() is None

    def test_returns_data_if_used(self, mock_oximy_dir):
        """Should return the full dict when status='used'."""
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": "sug-1", "status": "used", "playbook": {"id": "pb-1"}}
        suggestions_file.write_text(json.dumps(payload))

        result = read_suggestion_feedback()
        assert result is not None
        assert result["status"] == "used"
        assert result["id"] == "sug-1"

    def test_returns_data_if_dismissed(self, mock_oximy_dir):
        """Should return the full dict when status='dismissed'."""
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": "sug-2", "status": "dismissed"}
        suggestions_file.write_text(json.dumps(payload))

        result = read_suggestion_feedback()
        assert result is not None
        assert result["status"] == "dismissed"

    def test_returns_none_on_invalid_json(self, mock_oximy_dir):
        """Should return None if file contains invalid JSON."""
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text("not valid json{{{")

        assert read_suggestion_feedback() is None

    def test_returns_none_on_empty_status(self, mock_oximy_dir):
        """Should return None if status field is missing or empty."""
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text(json.dumps({"id": "sug-3"}))

        assert read_suggestion_feedback() is None


# =============================================================================
# clear_suggestion
# =============================================================================


class TestClearSuggestion:
    def test_deletes_file(self, mock_oximy_dir):
        """Should delete suggestions.json if it exists."""
        _, suggestions_file = mock_oximy_dir
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
        _, suggestions_file = mock_oximy_dir
        suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        suggestions_file.write_text("{}")

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            clear_suggestion()

        assert "Failed to clear suggestion file" in caplog.text
