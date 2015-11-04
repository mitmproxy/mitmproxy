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
        -p 443
        -s dns_spoofing.py
        # Used as the target location if neither SNI nor host header are present.
        -R http://example.com/
    mitmdump
        -p 80
        -R http://localhost:443/

    (Setting up a single proxy instance and using iptables to redirect to it
    works as well)
"""
import re


# This regex extracts splits the host header into host and port.
# Handles the edge case of IPv6 addresses containing colons.
# https://bugzilla.mozilla.org/show_bug.cgi?id=45891
parse_host_header = re.compile(r"^(?P<host>[^:]+|\[.+\])(?::(?P<port>\d+))?$")


def request(context, flow):
    if flow.client_conn.ssl_established:
        flow.request.scheme = "https"
        sni = flow.client_conn.connection.get_servername()
        port = 443
    else:
        flow.request.scheme = "http"
        sni = None
        port = 80

    host_header = flow.request.pretty_host
    m = parse_host_header.match(host_header)
    if m:
        host_header = m.group("host").strip("[]")
        if m.group("port"):
            port = int(m.group("port"))

    flow.request.host = sni or host_header
    flow.request.port = port