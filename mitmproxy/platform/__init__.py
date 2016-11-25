import re
import socket
import sys
from typing import Tuple


def init_transparent_mode() -> None:
    """
    Initialize transparent mode.
    """


def original_addr(csock: socket.socket) -> Tuple[str, int]:
    """
    Get the original destination for the given socket.
    Will be None if transparent mode is not supported.
    """


if re.match(r"linux(?:2)?", sys.platform):
    from . import linux

    original_addr = linux.original_addr
elif sys.platform == "darwin" or sys.platform.startswith("freebsd"):
    from . import osx

    original_addr = osx.original_addr
elif sys.platform == "win32":
    from . import windows

    resolver = windows.Resolver()
    init_transparent_mode = resolver.setup
    original_addr = resolver.original_addr
else:
    original_addr = None
