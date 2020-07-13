"""
Mirror all web pages.

Useful if you are living down under.
"""
from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    reflector = b"<style>body {transform: scaleX(-1);}</style></head>"
    flow.response.content = flow.response.content.replace(b"</head>", reflector)
