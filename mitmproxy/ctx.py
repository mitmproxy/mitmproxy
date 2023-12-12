from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import mitmproxy.log
    import mitmproxy.master
    import mitmproxy.options

log: mitmproxy.log.Log
master: mitmproxy.master.Master
options: mitmproxy.options.Options
