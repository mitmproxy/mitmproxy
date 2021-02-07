#!/usr/bin/env python
"""
Read a mitmproxy dump file.
"""
from mitmproxy import io, http, websocket
from mitmproxy.exceptions import FlowReadException
import pprint
import sys

with open(sys.argv[1], "rb") as logfile:
    freader = io.FlowReader(logfile)
    pp = pprint.PrettyPrinter(indent=4)
    try:
        for f in freader.stream():
            print(f)
            if isinstance(f, http.HTTPFlow):
                print(f.request.host)
            elif isinstance(f, websocket.WebSocketFlow):
                print(f.server_conn.address[0])
            pp.pprint(f.get_state())
            print("")
    except FlowReadException as e:
        print(f"Flow file corrupted: {e}")
