"""
Oximy Addon for mitmproxy

Lightweight AI traffic capture with whitelist/blacklist filtering.
Supports HTTP/REST, SSE, WebSocket, HTTP/2, HTTP/3, gRPC.
Saves raw request/response bodies to JSONL files.
"""

from mitmproxy.addons.oximy.addon import OximyAddon

__all__ = ["OximyAddon"]

# For use with `mitmdump -s .../oximy/__init__.py`
addons = [OximyAddon()]
