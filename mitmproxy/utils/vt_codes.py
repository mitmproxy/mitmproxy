"""
This module provides a method to detect if a given file object supports virtual terminal escape codes.
"""

import os
import sys
from typing import IO

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

    def ensure_supported(f: IO[str]) -> bool:
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

    def ensure_supported(f: IO[str]) -> bool:
        return f.isatty()
