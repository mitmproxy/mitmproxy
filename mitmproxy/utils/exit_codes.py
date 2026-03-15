"""
Individual exit codes for mitmproxy.

See https://github.com/mitmproxy/mitmproxy/issues/5696
"""

SUCCESS = 0

GENERIC_ERROR = 1

# Startup
STARTUP_ERROR = 10

# Terminal/console
NO_TTY = 20

# Arguments and options
INVALID_ARGS = 30
INVALID_OPTIONS = 31

# I/O
CANNOT_PRINT = 40
CANNOT_WRITE_TO_FILE = 41
