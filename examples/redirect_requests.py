from libmproxy.protocol.http import HTTPResponse
from netlib.odict import ODictCaseless

"""
This example shows two ways to redirect flows to other destinations.
"""


def request(context, flow):
    if flow.request.pretty_host(hostheader=True).endswith("example.com"):
        resp = HTTPResponse(
            [1, 1], 200, "OK",
            ODictCaseless([["Content-Type", "text/html"]]),
            "helloworld")
        flow.reply(resp)
    if flow.request.pretty_host(hostheader=True).endswith("example.org"):
        flow.request.host = "mitmproxy.org"
        flow.request.update_host_header()
