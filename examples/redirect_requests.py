"""
This example shows two ways to redirect flows to other destinations.
"""
from mitmproxy.models import HTTPResponse
from netlib.http import Headers


def request(context, flow):
    # pretty_host takes the "Host" header of the request into account,
    # which is useful in transparent mode where we usually only have the IP
    # otherwise.

    # Method 1: Answer with a locally generated response
    if flow.request.pretty_host.endswith("example.com"):
        resp = HTTPResponse(
            b"HTTP/1.1", 200, b"OK",
            Headers(Content_Type="text/html"),
            b"helloworld")
        flow.reply.send(resp)

    # Method 2: Redirect the request to a different server
    if flow.request.pretty_host.endswith("example.org"):
        flow.request.host = "mitmproxy.org"
