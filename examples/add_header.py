#!/usr/bin/env python
"""
    This script adds a new header to all responses.
"""
from libmproxy import script

def response(ctx, f):
    f.response.headers["newheader"] = ["foo"]
