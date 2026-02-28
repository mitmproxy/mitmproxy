"""Server-driven proactive playbook suggestion writer.

Receives suggestions from the server via sensor-config and writes them
to ~/.oximy/suggestions.json for the Mac app to display.

Cooldown logic ensures suggestions respect rate-limit intervals even if
the server sends them early (race conditions, stale cache, etc.).
"""

import json
import logging
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path

logger = logging.getLogger(__name__)

OXIMY_DIR = Path("~/.oximy").expanduser()
SUGGESTIONS_FILE = OXIMY_DIR / "suggestions.json"
SUGGESTION_STATE_FILE = OXIMY_DIR / "suggestion-state.json"

DEFAULT_COOLDOWN_MINUTES = 5
DEFAULT_DISMISSAL_COOLDOWN_HOURS = 24

# --- Module-level cooldown state (fast in-memory, persisted to disk) ---
_cooldown_until: float = 0.0
_last_suggestion_id: str | None = None
_state_loaded: bool = False


def _ensure_state_loaded() -> None:
    """Lazy one-time load of cooldown state from disk."""
    global _cooldown_until, _last_suggestion_id, _state_loaded
    if _state_loaded:
        return
    _state_loaded = True
    try:
        if not SUGGESTION_STATE_FILE.exists():
            return
        with open(SUGGESTION_STATE_FILE) as f:
            data = json.load(f)
        cooldown_str = data.get("cooldownUntil")
        if cooldown_str:
            dt = datetime.fromisoformat(cooldown_str)
            _cooldown_until = dt.timestamp()
        _last_suggestion_id = data.get("lastSuggestionId")
    except Exception:
        _cooldown_until = 0.0
        _last_suggestion_id = None


def _save_state(last_action: str, last_action_at: datetime) -> None:
    """Persist cooldown state to disk for restart survival."""
    try:
        OXIMY_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "cooldownUntil": datetime.fromtimestamp(
                _cooldown_until, tz=timezone.utc
            ).isoformat(),
            "lastSuggestionId": _last_suggestion_id,
            "lastAction": last_action,
            "lastActionAt": last_action_at.isoformat(),
        }
        with open(SUGGESTION_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"[PLAYBOOK] Failed to save suggestion state: {e}")


def should_write_suggestion(suggestion_id: str) -> bool:
    """Check whether a suggestion should be written (cooldown + dedup gate).

    Returns False if we're in cooldown or the suggestion ID matches the
    last one written (deduplication for the 3-second polling loop).
    """
    _ensure_state_loaded()

    if suggestion_id and suggestion_id == _last_suggestion_id:
        logger.debug(
            f"[PLAYBOOK] Skipping duplicate suggestion: {suggestion_id}"
        )
        return False

    if time.time() < _cooldown_until:
        logger.debug(
            "[PLAYBOOK] Suggestion blocked by cooldown "
            f"(expires in {_cooldown_until - time.time():.0f}s)"
        )
        return False

    return True


def record_suggestion_feedback(
    action: str,
    cooldown_minutes: float | None = None,
    dismissal_cooldown_hours: float | None = None,
) -> None:
    """Start a cooldown after a suggestion is used or dismissed.

    - "dismissed" -> dismissal_cooldown_hours (default 24h)
    - "used" -> cooldown_minutes (default 5 min)
    """
    global _cooldown_until
    _ensure_state_loaded()

    now = time.time()
    if action == "dismissed":
        hours = (
            dismissal_cooldown_hours
            if dismissal_cooldown_hours is not None
            else DEFAULT_DISMISSAL_COOLDOWN_HOURS
        )
        _cooldown_until = now + hours * 3600
    else:
        minutes = (
            cooldown_minutes
            if cooldown_minutes is not None
            else DEFAULT_COOLDOWN_MINUTES
        )
        _cooldown_until = now + minutes * 60

    action_at = datetime.now(timezone.utc)
    _save_state(action, action_at)
    logger.info(
        f"[PLAYBOOK] Cooldown started: {action} → "
        f"expires in {_cooldown_until - now:.0f}s"
    )


def reset_suggestion_state() -> None:
    """Reset all module-level cooldown state. Used by tests."""
    global _cooldown_until, _last_suggestion_id, _state_loaded
    _cooldown_until = 0.0
    _last_suggestion_id = None
    _state_loaded = False


def write_suggestion_from_server(suggestion: dict) -> None:
    """Write server-provided suggestion to disk for the Mac app."""
    global _last_suggestion_id

    output = {
        "id": suggestion.get("id", ""),
        "playbook": {
            "id": suggestion.get("playbookId", ""),
            "name": suggestion.get("playbookName", ""),
            "description": suggestion.get("playbookDescription", ""),
            "category": suggestion.get("playbookCategory", ""),
            "promptTemplate": suggestion.get("promptTemplate", ""),
        },
        "confidence": suggestion.get("confidence", 0),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    try:
        OXIMY_DIR.mkdir(parents=True, exist_ok=True)
        with open(SUGGESTIONS_FILE, "w") as f:
            json.dump(output, f, indent=2)
        _last_suggestion_id = suggestion.get("id", "")
        logger.info(
            f"[PLAYBOOK] Server suggestion written: {suggestion.get('playbookName', '?')}"
        )
    except Exception as e:
        logger.warning(f"[PLAYBOOK] Failed to write suggestion: {e}")


def read_suggestion_feedback() -> dict | None:
    """Read suggestion feedback from the Mac app (status changed to used/dismissed).

    Returns the suggestion dict if feedback exists, None otherwise.
    """
    try:
        if not SUGGESTIONS_FILE.exists():
            return None

        with open(SUGGESTIONS_FILE) as f:
            data = json.load(f)

        status = data.get("status", "")
        if status in ("used", "dismissed"):
            return data

        return None
    except Exception:
        return None


def clear_suggestion() -> None:
    """Remove the suggestions file after feedback has been sent."""
    try:
        if SUGGESTIONS_FILE.exists():
            SUGGESTIONS_FILE.unlink()
    except Exception as e:
        logger.warning(f"[PLAYBOOK] Failed to clear suggestion file: {e}")
