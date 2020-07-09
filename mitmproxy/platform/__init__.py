import re
import socket
import sys
from typing import Callable, Optional, Tuple


def init_transparent_mode() -> None:
    """
    Initialize transparent mode.
    """


original_addr: Optional[Callable[[socket.socket], Tuple[str, int]]]
"""
Get the original destination for the given socket.
This function will be None if transparent mode is not supported.
"""

if re.match(r"linux(?:2)?", sys.platform):
    from . import linux

    original_addr = linux.original_addr
elif sys.platform == "darwin" or sys.platform.startswith("freebsd"):
    from . import osx

    original_addr = osx.original_addr
elif sys.platform.startswith("openbsd"):
    from . import openbsd

    original_addr = openbsd.original_addr
elif sys.platform == "win32":
    from . import windows

    resolver = windows.Resolver()
    init_transparent_mode = resolver.setup  # noqa
    original_addr = resolver.original_addr
else:
    original_addr = None

__all__ = [
    "original_addr",
    "init_transparent_mode"
]
