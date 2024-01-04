from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import mitmproxy.log
    import mitmproxy.master
    import mitmproxy.options

master: mitmproxy.master.Master
options: mitmproxy.options.Options

log: mitmproxy.log.Log
"""Deprecated: Use Python's builtin `logging` module instead."""
