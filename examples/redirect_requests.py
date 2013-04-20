from libmproxy.flow import Response
from netlib.odict import ODictCaseless

"""
This example shows two ways to redirect flows to other destinations.
"""

def request(context, flow):
    if flow.request.host.endswith("example.com"):
        resp = Response(flow.request,
                        [1,1],
                        200, "OK",
                        ODictCaseless([["Content-Type","text/html"]]),
                        "helloworld",
                        None)
        flow.request.reply(resp)
    if flow.request.host.endswith("example.org"):
        flow.request.host = "mitmproxy.org"
        flow.request.headers["Host"] = ["mitmproxy.org"]
