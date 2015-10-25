"""
This example shows two ways to redirect flows to other destinations.
"""
from libmproxy.models import HTTPResponse
from netlib.http import Headers

def request(context, flow):
    # pretty_host takes the "Host" header of the request into account,
    # which is useful in transparent mode where we usually only have the IP
    # otherwise.

    # Method 1: Answer with a locally generated response
    if flow.request.pretty_host.endswith("example.com"):
        resp = HTTPResponse(
            [1, 1], 200, "OK",
            Headers(Content_Type="text/html"),
            "helloworld")
        flow.reply(resp)
    
    # Method 1, another example.
    # Serve local binary file (/home/user/new_file.bin) for request URL (http://example.com/sample.bin)
    if flow.request.pretty_host.endswith("example.com") and flow.request.url == "/sample.bin":
        with open("/home/user/new_file.bin", "rb") as nfile:
            nfile_content = nfile.read()
        resp = HTTPResponse(
            [1, 1], 200, "OK",
            ODictCaseless([["Content-Type", "application/octet-stream"]]),
            nfile_content)
        flow.reply(resp)
    
    # Method 2: Redirect the request to a different server
    if flow.request.pretty_host.endswith("example.org"):
        flow.request.host = "mitmproxy.org"
    
