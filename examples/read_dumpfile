#!/usr/bin/env python
#
# Simple script showing how to read a mitmproxy dump file
#

from libmproxy import flow
import json, sys

with open("logfile", "rb") as f:
    freader = flow.FlowReader(f)
    try:
       for i in freader.stream():
            print i.request.host
            json.dump(i._get_state(), sys.stdout, indent=4)
            print ""
    except flow.FlowReadError, v:
        print "Flow file corrupted. Stopped loading."