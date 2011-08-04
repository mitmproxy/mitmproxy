"""
    This script adds a new header to all responses.
"""

def response(ctx, f):
    f.response.headers["newheader"] = ["foo"]
