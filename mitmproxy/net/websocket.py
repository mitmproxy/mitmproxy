"""
Collection of WebSocket protocol utility functions (RFC6455)
Spec: https://tools.ietf.org/html/rfc6455
"""


def check_handshake(headers):
    return (
            "upgrade" in headers.get("connection", "").lower() and
            headers.get("upgrade", "").lower() == "websocket" and
            (headers.get("sec-websocket-key") is not None or headers.get("sec-websocket-accept") is not None)
    )


def get_extensions(headers):
    return headers.get("sec-websocket-extensions", None)


def get_protocol(headers):
    return headers.get("sec-websocket-protocol", None)


def get_client_key(headers):
    return headers.get("sec-websocket-key", None)


def get_server_accept(headers):
    return headers.get("sec-websocket-accept", None)
