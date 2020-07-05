"""
This script simply prints all received HTTP Trailers.

HTTP requests and responses can container trailing headers which are sent after
the body is fully transmitted. Such trailers need to be announced in the initial
headers by name, so the receiving endpoint can wait and read them after the
body.
"""

from mitmproxy import http
from mitmproxy.net.http import Headers


def request(flow: http.HTTPFlow):
    if flow.request.trailers:
        print("HTTP Trailers detected! Request contains:", flow.request.trailers)


def response(flow: http.HTTPFlow):
    if flow.response.trailers:
        print("HTTP Trailers detected! Response contains:", flow.response.trailers)

    if flow.request.path == "/inject_trailers":
        flow.response.headers["trailer"] = "x-my-injected-trailer-header"
        flow.response.trailers = Headers([
            (b"x-my-injected-trailer-header", b"foobar")
        ])
        print("Injected a new trailer...", flow.response.headers["trailer"])
