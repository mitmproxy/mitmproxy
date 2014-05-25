from libmproxy.flow import Response
from netlib.odict import ODictCaseless

"""
This example shows two ways to redirect flows to other destinations.

NOTE:
    HTTPRequest attributes port and host are fill only if the HTTP request does
    contains an absolute URL (eg. GET http://host:port/path) otherwise they will be set to None.

    * You can detect the form with HTTPRequest.form_in (aka. flow.request.form_in).
    * You can override the form with --http-form-in argument
"""

def request(context, flow):
    # Check the host from an absolute URL
    # Should be used for upstream mode, manual override destination and default mode.
    if flow.request.host.endswith("example.com"):
        # Example #1: Create an hard-coded reply to the client
        resp = Response(flow.request,
                        [1,1],
                        200, "OK",
                        ODictCaseless([["Content-Type","text/html"]]),
                        "helloworld",
                        None)
        flow.request.reply(resp)

    # Check the host from a relative URL - Headers can be spoofed by user !
    # Should be used for transparent mode or reverse proxy mode.
    if any(host.endswith("example.com") for host in flow.request.headers["Host"]):

        # Exemple #2: Ask mitmproxy to connect to a different host
        flow.request.host = "mitmproxy.org"
        flow.request.headers["Host"] = ["mitmproxy.org"]
