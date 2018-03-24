#!/usr/bin/env python
from mitmproxy import options, optmanager
from mitmproxy.tools import dump, console, web

masters = {
    "mitmproxy": console.master.ConsoleMaster,
    "mitmdump": dump.DumpMaster,
    "mitmweb": web.master.WebMaster
}

for name, master in masters.items():
    opts = options.Options()
    inst = master(opts)
    print(optmanager.dump_dicts(opts))
