"""
Collection of WebSocket protocol utility functions (RFC6455)
Spec: https://tools.ietf.org/html/rfc6455
"""

import base64
import hashlib
import os

from wsproto.extensions import PerMessageDeflate

from mitmproxy.net import http
from mitmproxy.utils import strutils

MAGIC = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
VERSION = "13"


def client_handshake_headers(version=None, key=None, protocol=None, extensions=None):
    """
        Create the headers for a valid HTTP upgrade request. If Key is not
        specified, it is generated, and can be found in sec-websocket-key in
        the returned header set.

        Returns an instance of http.Headers
    """
    if version is None:
        version = VERSION
    if key is None:
        key = base64.b64encode(os.urandom(16)).decode('ascii')
    h = http.Headers(
        connection="upgrade",
        upgrade="websocket",
        sec_websocket_version=version,
        sec_websocket_key=key,
    )
    if protocol is not None:
        h['sec-websocket-protocol'] = protocol
    if extensions is not None:
        h['sec-websocket-extensions'] = extensions
    return h


def server_handshake_headers(client_key, protocol=None, extensions=None):
    """
      The server response is a valid HTTP 101 response.

      Returns an instance of http.Headers
    """
    h = http.Headers(
        connection="upgrade",
        upgrade="websocket",
        sec_websocket_accept=create_server_nonce(client_key),
    )
    if protocol is not None:
        h['sec-websocket-protocol'] = protocol
    if extensions is not None:
        h['sec-websocket-extensions'] = extensions
    return h


def check_handshake(headers):
    return (
        "upgrade" in headers.get("connection", "").lower() and
        headers.get("upgrade", "").lower() == "websocket" and
        (headers.get("sec-websocket-key") is not None or headers.get("sec-websocket-accept") is not None)
    )


def create_server_nonce(client_nonce):
    return base64.b64encode(hashlib.sha1(strutils.always_bytes(client_nonce) + MAGIC).digest())


def check_client_version(headers):
    return headers.get("sec-websocket-version", "") == VERSION


def get_extensions(headers):
    return headers.get("sec-websocket-extensions", None)


def get_protocol(headers):
    return headers.get("sec-websocket-protocol", None)


def get_client_key(headers):
    return headers.get("sec-websocket-key", None)


def get_server_accept(headers):
    return headers.get("sec-websocket-accept", None)


def make_extension(extension):
    name, *params = extension.split(';')
    if name == 'permessage-deflate':
        args = {
            "client_no_context_takeover": False,
            "server_no_context_takeover": False,
            "client_max_window_bits": None,
            "server_max_window_bits": None
        }

        for param in params:
            if param.startswith('client_no_context_takeover'):
                args["client_no_context_takeover"] = True
            elif param.startswith('server_no_context_takeover'):
                args["server_no_context_takeover"] = True
            elif param.startswith('client_max_window_bits'):
                args["client_max_window_bits"] = int(param.split('=', 1)[1].strip())
            elif param.startswith('server_max_window_bits'):
                args["server_max_window_bits"] = int(param.split('=', 1)[1].strip())

        return PerMessageDeflate(**args)
