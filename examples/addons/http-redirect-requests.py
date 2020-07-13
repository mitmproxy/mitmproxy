"""Redirect HTTP requests to another server."""
from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    # pretty_host takes the "Host" header of the request into account,
    # which is useful in transparent mode where we usually only have the IP
    # otherwise.
    if flow.request.pretty_host == "example.org":
        flow.request.host = "mitmproxy.org"
