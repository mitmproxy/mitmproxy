"""Server-driven proactive playbook suggestion writer.

Receives suggestions from the server via sensor-config and writes them
to ~/.oximy/suggestions.json for the Mac app to display.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

OXIMY_DIR = Path("~/.oximy").expanduser()
SUGGESTIONS_FILE = OXIMY_DIR / "suggestions.json"


def write_suggestion_from_server(suggestion: dict) -> None:
    """Write server-provided suggestion to disk for the Mac app."""
    output = {
        "id": suggestion.get("id", ""),
        "playbook": {
            "id": suggestion.get("playbookId", ""),
            "name": suggestion.get("playbookName", ""),
            "description": suggestion.get("playbookDescription", ""),
            "category": suggestion.get("playbookCategory", ""),
            "prompt_template": suggestion.get("promptTemplate", ""),
        },
        "confidence": suggestion.get("confidence", 0),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    try:
        OXIMY_DIR.mkdir(parents=True, exist_ok=True)
        with open(SUGGESTIONS_FILE, "w") as f:
            json.dump(output, f, indent=2)
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
