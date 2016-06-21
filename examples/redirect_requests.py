"""
This example shows two ways to redirect flows to other destinations.
"""
from mitmproxy.models import HTTPResponse
from netlib.http import Headers
from mitmproxy import ctx


def request():
    # pretty_host takes the "Host" header of the request into account,
    # which is useful in transparent mode where we usually only have the IP
    # otherwise.

    # Method 1: Answer with a locally generated response
    if ctx.flow.request.pretty_host.endswith("example.com"):
        resp = HTTPResponse(
            "HTTP/1.1", 200, "OK",
            Headers(Content_Type="text/html"),
            "helloworld")
        ctx.flow.reply.send(resp)

    # Method 2: Redirect the request to a different server
    if ctx.flow.request.pretty_host.endswith("example.org"):
        ctx.flow.request.host = "mitmproxy.org"
