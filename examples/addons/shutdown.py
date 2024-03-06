"""
A simple way of shutting down the mitmproxy instance to stop everything.

Usage:

    mitmproxy -s shutdown.py

    and then send a HTTP request to trigger the shutdown:
    curl --proxy localhost:8080 http://example.com/path
"""

import logging

from mitmproxy import ctx
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    # a random condition to make this example a bit more interactive
    if flow.request.pretty_url == "http://example.com/path":
        logging.info("Shutting down everything...")
        ctx.master.shutdown()
