from libmproxy.flow import Response
from netlib.odict import ODictCaseless

"""
This example shows two ways to redirect flows to other destinations.
"""

def request(context, flow):
    if any(host.endswith("example.com") for host in flow.request.headers["Host"]):
        resp = Response(flow.request,
                        [1,1],
                        200, "OK",
                        ODictCaseless([["Content-Type","text/html"]]),
                        "helloworld",
                        None)
        flow.request.reply(resp)
    if any(host.endswith("example.com") for host in flow.request.headers["Host"]):
        flow.request.host = "mitmproxy.org"
        flow.request.headers["Host"] = ["mitmproxy.org"]
