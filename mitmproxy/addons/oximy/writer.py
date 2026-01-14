"""
JSONL file writer with time-based rotation.

Writes events to daily JSONL files with atomic append operations.
Pattern inspired by mitmproxy/addons/save.py
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.models import OximyEvent

logger = logging.getLogger(__name__)


class EventWriter:
    """
    Writes OximyEvents to rotating JSONL files.

    Files are rotated daily with naming pattern: traces_YYYY-MM-DD.jsonl

    In test mode, writes pretty JSON to a single file (test_trace.json) that
    overwrites on each run for quick iteration.
    """

    def __init__(
        self,
        output_dir: Path | str,
        filename_pattern: str = "traces_{date}.jsonl",
        test_mode: bool = False,
    ):
        """
        Args:
            output_dir: Directory for output files
            filename_pattern: Filename pattern with {date} placeholder
            test_mode: If True, write pretty JSON to test_trace.json (overwrites)
        """
        self.output_dir = Path(output_dir).expanduser()
        self.filename_pattern = filename_pattern
        self.test_mode = test_mode
        self._current_file: Path | None = None
        self._fo: IO[str] | None = None
        self._event_count: int = 0
        self._test_events: list = []  # Buffer for test mode

    def write(self, event: OximyEvent) -> None:
        """
        Write an event to the current JSONL file.

        Rotates to a new file if the date has changed.
        In test mode, buffers events and writes pretty JSON on close.
        """
        if self.test_mode:
            # Test mode: buffer events and write pretty JSON
            self._test_events.append(event.to_dict())
            self._event_count += 1
            self._write_test_file()
            logger.info(f"Test mode: captured event #{self._event_count}")
            return

        self._maybe_rotate()

        if self._fo is None:
            logger.error("No file handle available for writing")
            return

        try:
            # Serialize and write (line-buffered mode flushes after each \n)
            line = json.dumps(event.to_dict(), separators=(",", ":"))
            self._fo.write(line + "\n")
            self._event_count += 1

        except (IOError, OSError) as e:
            logger.error(f"Failed to write event: {e}")

    def _write_test_file(self) -> None:
        """Write buffered events to test_trace.json as pretty JSON."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.output_dir / "test_trace.json"

            # Write as a JSON array with pretty formatting
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(self._test_events, f, indent=2)

            self._current_file = test_file
            logger.info(f"Test trace written to: {test_file}")

        except (IOError, OSError) as e:
            logger.error(f"Failed to write test trace: {e}")

    def _maybe_rotate(self) -> None:
        """Rotate to a new file if the date has changed."""
        expected_file = self._get_current_filepath()

        if self._current_file == expected_file:
            return

        # Close existing file
        if self._fo is not None:
            try:
                self._fo.close()
            except IOError:
                pass
            self._fo = None

        # Create directory if needed
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create output directory: {e}")
            return

        # Open new file in append mode with line buffering (buffering=1)
        # Line buffering ensures each event is flushed after the newline
        # This is critical for a monitoring system - no data loss on crash
        try:
            self._fo = open(expected_file, "a", encoding="utf-8", buffering=1)
            self._current_file = expected_file
            logger.info(f"Opened trace file: {expected_file}")
        except IOError as e:
            logger.error(f"Failed to open trace file: {e}")

    def _get_current_filepath(self) -> Path:
        """Get the filepath for the current date."""
        today = date.today().isoformat()  # YYYY-MM-DD
        filename = self.filename_pattern.format(date=today)
        return self.output_dir / filename

    def close(self) -> None:
        """Close the current file handle."""
        if self.test_mode:
            # Final write for test mode
            if self._test_events:
                self._write_test_file()
                logger.info(f"Test mode complete: {self._event_count} events in {self._current_file}")
            self._test_events.clear()
            return

        if self._fo is not None:
            try:
                self._fo.close()
                logger.info(f"Closed trace file (wrote {self._event_count} events)")
            except IOError as e:
                logger.error(f"Failed to close trace file: {e}")
            finally:
                self._fo = None
                self._current_file = None

    @property
    def current_file(self) -> Path | None:
        """Get the current output file path."""
        return self._current_file

    @property
    def event_count(self) -> int:
        """Get the total number of events written."""
        return self._event_count

    def __enter__(self) -> EventWriter:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        _ = exc_type, exc_val, exc_tb
        self.close()
