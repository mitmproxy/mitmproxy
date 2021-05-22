"""Modify HTTP query parameters."""
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    flow.request.query["mitmproxy"] = "rocks"
