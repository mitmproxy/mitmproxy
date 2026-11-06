"""
This module provides a method to detect if a given file object supports virtual terminal escape codes.
"""

import os
import sys
from typing import IO
from typing import Literal

ColorOverride = Literal["auto", "always", "never"]

if os.name == "nt":
    from ctypes import byref  # type: ignore
    from ctypes import windll  # type: ignore
    from ctypes.wintypes import BOOL
    from ctypes.wintypes import DWORD
    from ctypes.wintypes import HANDLE
    from ctypes.wintypes import LPDWORD

    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # https://docs.microsoft.com/de-de/windows/console/getstdhandle
    GetStdHandle = windll.kernel32.GetStdHandle
    GetStdHandle.argtypes = [DWORD]
    GetStdHandle.restype = HANDLE

    # https://docs.microsoft.com/de-de/windows/console/getconsolemode
    GetConsoleMode = windll.kernel32.GetConsoleMode
    GetConsoleMode.argtypes = [HANDLE, LPDWORD]
    GetConsoleMode.restype = BOOL

    # https://docs.microsoft.com/de-de/windows/console/setconsolemode
    SetConsoleMode = windll.kernel32.SetConsoleMode
    SetConsoleMode.argtypes = [HANDLE, DWORD]
    SetConsoleMode.restype = BOOL

    def _ensure_supported_native(f: IO[str]) -> bool:
        if not f.isatty():
            return False
        if f == sys.stdout:
            h = STD_OUTPUT_HANDLE
        elif f == sys.stderr:
            h = STD_ERROR_HANDLE
        else:
            return False

        handle = GetStdHandle(h)
        console_mode = DWORD()
        ok = GetConsoleMode(handle, byref(console_mode))
        if not ok:
            return False

        ok = SetConsoleMode(
            handle, console_mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        )
        return ok

else:

    def _ensure_supported_native(f: IO[str]) -> bool:
        return f.isatty()


def ensure_supported(f: IO[str], override: ColorOverride = "auto") -> bool:
    """Return whether ``f`` supports virtual terminal escape codes.

    The ``override`` parameter mirrors the well-known ``--color={auto,always,never}``
    flag from coreutils (``ls``, ``grep``):

    - ``"auto"`` (default): probe the file via ``isatty()`` (and on Windows, the
      console mode ioctl). This preserves the historical behavior.
    - ``"always"``: unconditionally return ``True``, e.g. when piping mitmdump
      output to a pager (``mitmdump | less -R``) and you want to keep colors.
    - ``"never"``: unconditionally return ``False``, e.g. when redirecting to a
      log file or running in a CI environment that mishandles ANSI codes.
    """
    if override == "always":
        return True
    if override == "never":
        return False
    return _ensure_supported_native(f)
