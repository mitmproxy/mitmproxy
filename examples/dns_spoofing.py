"""
This inline scripts makes it possible to use mitmproxy in scenarios where IP spoofing has been used to redirect
connections to mitmproxy. The way this works is that we rely on either the TLS Server Name Indication (SNI) or the
Host header of the HTTP request.
Of course, this is not foolproof - if an HTTPS connection comes without SNI, we don't
know the actual target and cannot construct a certificate that looks valid.
Similarly, if there's no Host header or a spoofed Host header, we're out of luck as well.
Using transparent mode is the better option most of the time.

Usage:
    mitmproxy
        -p 80
        -R http://example.com/  // Used as the target location if no Host header is present
    mitmproxy
        -p 443
        -R https://example.com/ // Used as the target locaction if neither SNI nor host header are present.

mitmproxy will always connect to the default location first, so it must be reachable.
As a workaround, you can spawn an arbitrary HTTP server and use that for both endpoints, e.g.
mitmproxy -p  80 -R       http://localhost:8000
mitmproxy -p 443 -R https2http://localhost:8000
"""


def request(context, flow):
    if flow.client_conn.ssl_established:
        # TLS SNI or Host header
        flow.request.host = flow.client_conn.connection.get_servername(
        ) or flow.request.pretty_host(hostheader=True)

        # If you use a https2http location as default destination, these
        # attributes need to be corrected as well:
        flow.request.port = 443
        flow.request.scheme = "https"
    else:
        # Host header
        flow.request.host = flow.request.pretty_host(hostheader=True)
