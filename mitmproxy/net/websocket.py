"""
Collection of WebSocket protocol utility functions (RFC6455)
Spec: https://tools.ietf.org/html/rfc6455
"""


import base64
import hashlib
import os
import struct

from wsproto.utilities import ACCEPT_GUID
from wsproto.handshake import WEBSOCKET_VERSION
from wsproto.frame_protocol import RsvBits, Header, Frame, XorMaskerSimple, XorMaskerNull

from mitmproxy.net import http
from mitmproxy.utils import bits, strutils


def read_frame(rfile, parse=True):
    """
    Reads a full WebSocket frame from a file-like object.

    Returns a parsed frame header, parsed frame, and the consumed bytes.
    """

    consumed_bytes = b''

    def consume(len):
        nonlocal consumed_bytes
        d = rfile.safe_read(len)
        consumed_bytes += d
        return d

    first_byte, second_byte = consume(2)
    fin = bits.getbit(first_byte, 7)
    rsv1 = bits.getbit(first_byte, 6)
    rsv2 = bits.getbit(first_byte, 5)
    rsv3 = bits.getbit(first_byte, 4)
    opcode = first_byte & 0xF
    mask_bit = bits.getbit(second_byte, 7)
    length_code = second_byte & 0x7F

    # payload_len > 125 indicates you need to read more bytes
    # to get the actual payload length
    if length_code <= 125:
        payload_len = length_code
    elif length_code == 126:
        payload_len, = struct.unpack("!H", consume(2))
    else:  # length_code == 127:
        payload_len, = struct.unpack("!Q", consume(8))

    # masking key only present if mask bit set
    if mask_bit == 1:
        masking_key = consume(4)
        masker = XorMaskerSimple(masking_key)
    else:
        masking_key = None
        masker = XorMaskerNull()

    masked_payload = consume(payload_len)

    if parse:
        header = Header(
            fin=fin,
            rsv=RsvBits(rsv1, rsv2, rsv3),
            opcode=opcode,
            payload_len=payload_len,
            masking_key=masking_key,
        )
        frame = Frame(
            opcode=opcode,
            payload=masker.process(masked_payload),
            frame_finished=fin,
            message_finished=fin
        )
    else:
        header = None
        frame = None

    return header, frame, consumed_bytes


def client_handshake_headers(version=None, key=None, protocol=None, extensions=None):
    """
    Create the headers for a valid HTTP upgrade request. If Key is not
    specified, it is generated, and can be found in sec-websocket-key in
    the returned header set.

    Returns an instance of http.Headers
    """
    if version is None:
        version = WEBSOCKET_VERSION
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
    return base64.b64encode(hashlib.sha1(strutils.always_bytes(client_nonce) + ACCEPT_GUID).digest())


def check_client_version(headers):
    return headers.get("sec-websocket-version", "") == WEBSOCKET_VERSION


def get_extensions(headers):
    return headers.get("sec-websocket-extensions", None)


def get_protocol(headers):
    return headers.get("sec-websocket-protocol", None)


def get_client_key(headers):
    return headers.get("sec-websocket-key", None)


def get_server_accept(headers):
    return headers.get("sec-websocket-accept", None)
