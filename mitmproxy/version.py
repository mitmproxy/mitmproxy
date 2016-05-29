from __future__ import (absolute_import, print_function, division)

from netlib.version import VERSION, IVERSION

NAME = "mitmproxy"
NAMEVERSION = NAME + " " + VERSION

__all__ = [
    "NAME",
    "NAMEVERSION",
    "VERSION",
    "IVERSION",
]
