from __future__ import absolute_import

import base64
import hashlib
import os
import struct
import io

from . import utils, odict

# Colleciton of utility functions that implement small portions of the RFC6455
# WebSockets Protocol Useful for building WebSocket clients and servers.
#
# Emphassis is on readabilty, simplicity and modularity, not performance or
# completeness
#
# This is a work in progress and does not yet contain all the utilites need to
# create fully complient client/servers #
# Spec: https://tools.ietf.org/html/rfc6455

# The magic sha that websocket servers must know to prove they understand
# RFC6455
websockets_magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
VERSION = "13"
MAX_16_BIT_INT = (1 << 16)
MAX_64_BIT_INT = (1 << 64)


class OPCODE:
    CONTINUE = 0x00
    TEXT = 0x01
    BINARY = 0x02
    CLOSE = 0x08
    PING = 0x09
    PONG = 0x0a


def apply_mask(message, masking_key):
    """
    Data sent from the server must be masked to prevent malicious clients
    from sending data over the wire in predictable patterns

    This method both encodes and decodes strings with the provided mask

    Servers do not have to mask data they send to the client.
    https://tools.ietf.org/html/rfc6455#section-5.3
    """
    masks = [utils.bytes_to_int(byte) for byte in masking_key]
    result = ""
    for char in message:
        result += chr(ord(char) ^ masks[len(result) % 4])
    return result


def client_handshake_headers(key=None, version=VERSION):
    """
        Create the headers for a valid HTTP upgrade request. If Key is not
        specified, it is generated, and can be found in sec-websocket-key in
        the returned header set.

        Returns an instance of ODictCaseless
    """
    if not key:
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
    return odict.ODictCaseless([
        ('Connection', 'Upgrade'),
        ('Upgrade', 'websocket'),
        ('Sec-WebSocket-Key', key),
        ('Sec-WebSocket-Version', version)
    ])


def server_handshake_headers(key):
    """
      The server response is a valid HTTP 101 response.
    """
    return odict.ODictCaseless(
        [
            ('Connection', 'Upgrade'),
            ('Upgrade', 'websocket'),
            ('Sec-WebSocket-Accept', create_server_nonce(key))
        ]
    )


def get_payload_length_pair(payload_bytestring):
    """
     A websockets frame contains an initial length_code, and an optional
     extended length code to represent the actual length if length code is
     larger than 125
    """
    actual_length = len(payload_bytestring)

    if actual_length <= 125:
        length_code = actual_length
    elif actual_length >= 126 and actual_length <= 65535:
        length_code = 126
    else:
        length_code = 127
    return (length_code, actual_length)


def make_length_code(len):
    """
     A websockets frame contains an initial length_code, and an optional
     extended length code to represent the actual length if length code is
     larger than 125
    """
    if len <= 125:
        return len
    elif len >= 126 and len <= 65535:
        return 126
    else:
        return 127


def check_client_handshake(headers):
    if headers.get_first("upgrade", None) != "websocket":
        return
    return headers.get_first('sec-websocket-key')


def check_server_handshake(headers):
    if headers.get_first("upgrade", None) != "websocket":
        return
    return headers.get_first('sec-websocket-accept')


def create_server_nonce(client_nonce):
    return base64.b64encode(
        hashlib.sha1(client_nonce + websockets_magic).hexdigest().decode('hex')
    )


def frame_header_bytes(
    opcode = 0,
    payload_length = 0,
    fin = 0,
    rsv1 = 0,
    rsv2 = 0,
    rsv3 = 0,
    mask = 0,
    masking_key = None,
    length_code = None
):
    first_byte = (fin << 7) | (rsv1 << 6) |\
                 (rsv2 << 4) | (rsv3 << 4) | opcode

    if length_code is None:
        length_code = make_length_code(payload_length)

    second_byte = (mask << 7) | length_code

    b = chr(first_byte) + chr(second_byte)

    if payload_length < 126:
        pass
    elif payload_length < MAX_16_BIT_INT:
        # '!H' pack as 16 bit unsigned short
        # add 2 byte extended payload length
        b += struct.pack('!H', payload_length)
    elif payload_length < MAX_64_BIT_INT:
        # '!Q' = pack as 64 bit unsigned long long
        # add 8 bytes extended payload length
        b += struct.pack('!Q', payload_length)
    if masking_key is not None:
        b += masking_key
    return b


class Frame(object):
    """
        Represents one websockets frame.
        Constructor takes human readable forms of the frame components
        from_bytes() is also avaliable.

        WebSockets Frame as defined in RFC6455

          0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
         +-+-+-+-+-------+-+-------------+-------------------------------+
         |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
         |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
         |N|V|V|V|       |S|             |   (if payload len==126/127)   |
         | |1|2|3|       |K|             |                               |
         +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
         |     Extended payload length continued, if payload len == 127  |
         + - - - - - - - - - - - - - - - +-------------------------------+
         |                               |Masking-key, if MASK set to 1  |
         +-------------------------------+-------------------------------+
         | Masking-key (continued)       |          Payload Data         |
         +-------------------------------- - - - - - - - - - - - - - - - +
         :                     Payload Data continued ...                :
         + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
         |                     Payload Data continued ...                |
         +---------------------------------------------------------------+
    """
    def __init__(
        self,
        fin,                          # decmial integer 1 or 0
        opcode,                       # decmial integer 1 - 4
        mask_bit,                     # decimal integer 1 or 0
        payload_length_code,          # decimal integer 1 - 127
        decoded_payload,              # bytestring
        rsv1 = 0,                     # decimal integer 1 or 0
        rsv2 = 0,                     # decimal integer 1 or 0
        rsv3 = 0,                     # decimal integer 1 or 0
        payload = None,               # bytestring
        masking_key = None,           # 32 bit byte string
        actual_payload_length = None, # any decimal integer
    ):
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask_bit = mask_bit
        self.payload_length_code = payload_length_code
        self.masking_key = masking_key
        self.payload = payload
        self.decoded_payload = decoded_payload
        self.actual_payload_length = actual_payload_length

    @classmethod
    def default(cls, message, from_client = False):
        """
          Construct a basic websocket frame from some default values.
          Creates a non-fragmented text frame.
        """
        length_code, actual_length = get_payload_length_pair(message)

        if from_client:
            mask_bit = 1
            # Random masking key
            masking_key = os.urandom(4)
            payload = apply_mask(message, masking_key)
        else:
            mask_bit = 0
            masking_key = None
            payload = message

        return cls(
            fin = 1, # final frame
            opcode = OPCODE.TEXT, # text
            mask_bit = mask_bit,
            payload_length_code = length_code,
            payload = payload,
            masking_key = masking_key,
            decoded_payload = message,
            actual_payload_length = actual_length
        )

    def is_valid(self):
        """
            Validate websocket frame invariants, call at anytime to ensure the
            Frame has not been corrupted.
        """
        constraints = [
            0 <= self.fin <= 1,
            0 <= self.rsv1 <= 1,
            0 <= self.rsv2 <= 1,
            0 <= self.rsv3 <= 1,
            1 <= self.opcode <= 4,
            0 <= self.mask_bit <= 1,
            1 <= self.payload_length_code <= 127,
            self.actual_payload_length == len(self.payload),
            1 <= len(self.masking_key) <= 4 if self.mask_bit else True,
            self.masking_key is not None if self.mask_bit else True
        ]
        if not all(constraints):
            return False
        elif self.payload and self.masking_key:
            decoded = apply_mask(self.payload, self.masking_key)
            if decoded != self.decoded_payload:
                return False
        return True

    def human_readable(self): # pragma: nocover
        return "\n".join([
            ("fin                   - " + str(self.fin)),
            ("rsv1                  - " + str(self.rsv1)),
            ("rsv2                  - " + str(self.rsv2)),
            ("rsv3                  - " + str(self.rsv3)),
            ("opcode                - " + str(self.opcode)),
            ("mask_bit              - " + str(self.mask_bit)),
            ("payload_length_code   - " + str(self.payload_length_code)),
            ("masking_key           - " + repr(str(self.masking_key))),
            ("payload               - " + repr(str(self.payload))),
            ("decoded_payload       - " + repr(str(self.decoded_payload))),
            ("actual_payload_length - " + str(self.actual_payload_length))
        ])

    @classmethod
    def from_bytes(cls, bytestring):
        """
          Construct a websocket frame from an in-memory bytestring
          to construct a frame from a stream of bytes, use from_file() directly
        """
        return cls.from_file(io.BytesIO(bytestring))

    def to_bytes(self):
        """
            Serialize the frame back into the wire format, returns a bytestring
            If you haven't checked is_valid_frame() then there's no guarentees
            that the serialized bytes will be correct. see safe_to_bytes()
        """
        b = frame_header_bytes(
            opcode = self.opcode,
            fin = self.fin,
            rsv1 = self.rsv1,
            rsv2 = self.rsv2,
            rsv3 = self.rsv3,
            mask = self.mask_bit,
            masking_key = self.masking_key,
            payload_length = self.actual_payload_length
        )
        b += self.payload # already will be encoded if neccessary
        return b

    def to_file(self, writer):
        writer.write(self.to_bytes())
        writer.flush()

    @classmethod
    def from_file(cls, fp):
        """
          read a websockets frame sent by a server or client

          fp is a "file like" object that could be backed by a network
          stream or a disk or an in memory stream reader
        """
        first_byte = utils.bytes_to_int(fp.read(1))
        second_byte = utils.bytes_to_int(fp.read(1))

        # grab the left most bit
        fin = first_byte >> 7
        # grab right most 4 bits by and-ing with 00001111
        opcode = first_byte & 15
        # grab left most bit
        mask_bit = second_byte >> 7
        # grab the next 7 bits
        payload_length = second_byte & 127

        # payload_lengthy > 125 indicates you need to read more bytes
        # to get the actual payload length
        if payload_length <= 125:
            actual_payload_length = payload_length

        elif payload_length == 126:
            actual_payload_length = utils.bytes_to_int(fp.read(2))

        elif payload_length == 127:
            actual_payload_length = utils.bytes_to_int(fp.read(8))

        # masking key only present if mask bit set
        if mask_bit == 1:
            masking_key = fp.read(4)
        else:
            masking_key = None

        payload = fp.read(actual_payload_length)

        if mask_bit == 1:
            decoded_payload = apply_mask(payload, masking_key)
        else:
            decoded_payload = payload

        return cls(
            fin = fin,
            opcode = opcode,
            mask_bit = mask_bit,
            payload_length_code = payload_length,
            payload = payload,
            masking_key = masking_key,
            decoded_payload = decoded_payload,
            actual_payload_length = actual_payload_length
        )

    def __eq__(self, other):
        return (
            self.fin == other.fin and
            self.rsv1 == other.rsv1 and
            self.rsv2 == other.rsv2 and
            self.rsv3 == other.rsv3 and
            self.opcode == other.opcode and
            self.mask_bit == other.mask_bit and
            self.payload_length_code == other.payload_length_code and
            self.masking_key == other.masking_key and
            self.payload == other.payload and
            self.decoded_payload == other.decoded_payload and
            self.actual_payload_length == other.actual_payload_length
        )
