"""Exit codes for mitmproxy processes."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERIC_ERROR = 1

    # Startup & Initialization errors (10-19)
    STARTUP_ERROR = 10

    # Environment & Console errors (20-29)
    NO_UTF_CONSOLE = 20
    NO_TTY = 21

    # Configuration & CLI Argument errors (30-39)
    INVALID_ARGS = 30
    INVALID_OPTIONS = 31

    # I/O errors (40-49)
    CANNOT_PRINT = 40
    CANNOT_WRITE_TO_FILE = 41


SUCCESS = ExitCode.SUCCESS
GENERIC_ERROR = ExitCode.GENERIC_ERROR

STARTUP_ERROR = ExitCode.STARTUP_ERROR

NO_UTF_CONSOLE = ExitCode.NO_UTF_CONSOLE
NO_TTY = ExitCode.NO_TTY

INVALID_ARGS = ExitCode.INVALID_ARGS
INVALID_OPTIONS = ExitCode.INVALID_OPTIONS

CANNOT_PRINT = ExitCode.CANNOT_PRINT
CANNOT_WRITE_TO_FILE = ExitCode.CANNOT_WRITE_TO_FILE
