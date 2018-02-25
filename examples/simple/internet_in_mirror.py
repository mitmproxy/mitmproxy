"""
This script reflects all content passing through the proxy.
"""
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    reflector = b"<style>body {transform: scaleX(-1);}</style></head>"
    flow.response.content = flow.response.content.replace(b"</head>", reflector)
