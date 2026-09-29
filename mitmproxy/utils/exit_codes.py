"""Process exit codes used across mitmproxy / mitmdump / mitmweb.

A parent process (CI, supervisor, watcher script, ...) only sees the integer
exit code returned by the tool, so funnelling every fatal path through
``sys.exit(1)`` makes it impossible to distinguish "you typed --invalid-opt"
from "the file we're saving flows to became unwritable mid-stream". Each
fatal branch picks the most specific code from this module instead.

Codes are grouped in tens so future additions can slot into the appropriate
category without renumbering everything that already shipped:

  10–19   startup-time problems
  20–29   environment problems (no TTY, missing UTF-8, etc.)
  30–39   user-supplied-input problems (argv parsing, options resolution)
  40–49   I/O problems (cannot print, cannot write to disk)
  50–59   debugging hooks (MITMPROXY_DEBUG_EXIT, etc.)

The existing ``1`` is preserved as ``GENERIC_ERROR`` for any path the
caller hasn't categorised yet — it's still wired in to keep "catch-all"
behaviour explicit at the call site.
"""

GENERIC_ERROR = 1

# 10-19: startup-time problems
STARTUP_ERROR = 10

# 20-29: environment problems
NO_UTF_CONSOLE = 20
NO_TTY = 21

# 30-39: user-supplied input problems
INVALID_ARGS = 30
INVALID_OPTIONS = 31

# 40-49: I/O problems
CANNOT_PRINT = 40
CANNOT_WRITE_TO_FILE = 41

# 50-59: debugging hooks
DEBUG_EXIT = 50
