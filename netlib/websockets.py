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


DEFAULT = object()


class FrameHeader:
    def __init__(
        self,
        opcode = OPCODE.TEXT,
        payload_length = 0,
        fin = False,
        rsv1 = False,
        rsv2 = False,
        rsv3 = False,
        masking_key = None,
        mask = DEFAULT,
        length_code = DEFAULT
    ):
        if not 0 <= opcode < 2 ** 4:
            raise ValueError("opcode must be 0-16")
        self.opcode = opcode
        self.payload_length = payload_length
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.mask = mask
        self.masking_key = masking_key
        self.length_code = length_code

    def to_bytes(self):
        first_byte = utils.setbit(0, 7, self.fin)
        first_byte = utils.setbit(first_byte, 6, self.rsv1)
        first_byte = utils.setbit(first_byte, 5, self.rsv2)
        first_byte = utils.setbit(first_byte, 4, self.rsv3)
        first_byte = first_byte | self.opcode

        if self.length_code is DEFAULT:
            length_code = make_length_code(self.payload_length)
        else:
            length_code = self.length_code

        if self.mask is DEFAULT:
            mask = bool(self.masking_key)
        else:
            mask = self.mask

        second_byte = (mask << 7) | length_code

        b = chr(first_byte) + chr(second_byte)

        if self.payload_length < 126:
            pass
        elif self.payload_length < MAX_16_BIT_INT:
            # '!H' pack as 16 bit unsigned short
            # add 2 byte extended payload length
            b += struct.pack('!H', self.payload_length)
        elif self.payload_length < MAX_64_BIT_INT:
            # '!Q' = pack as 64 bit unsigned long long
            # add 8 bytes extended payload length
            b += struct.pack('!Q', self.payload_length)
        if self.masking_key is not None:
            b += self.masking_key
        return b

    @classmethod
    def from_file(klass, fp):
        """
          read a websockets frame header
        """
        first_byte = utils.bytes_to_int(fp.read(1))
        second_byte = utils.bytes_to_int(fp.read(1))

        fin = utils.getbit(first_byte, 7)
        rsv1 = utils.getbit(first_byte, 6)
        rsv2 = utils.getbit(first_byte, 5)
        rsv3 = utils.getbit(first_byte, 4)
        # grab right most 4 bits by and-ing with 00001111
        opcode = first_byte & 15
        # grab left most bit
        mask_bit = second_byte >> 7
        # grab the next 7 bits
        length_code = second_byte & 127

        # payload_lengthy > 125 indicates you need to read more bytes
        # to get the actual payload length
        if length_code <= 125:
            payload_length = length_code
        elif length_code == 126:
            payload_length = utils.bytes_to_int(fp.read(2))
        elif length_code == 127:
            payload_length = utils.bytes_to_int(fp.read(8))

        # masking key only present if mask bit set
        if mask_bit == 1:
            masking_key = fp.read(4)
        else:
            masking_key = None

        return klass(
            fin = fin,
            rsv1 = rsv1,
            rsv2 = rsv2,
            rsv3 = rsv3,
            opcode = opcode,
            mask = mask_bit,
            length_code = length_code,
            payload_length = payload_length,
            masking_key = masking_key,
        )

    def __eq__(self, other):
        return self.to_bytes() == other.to_bytes()


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
    def __init__(self, payload = "", **kwargs):
        self.payload = payload
        kwargs["payload_length"] = kwargs.get("payload_length", len(payload))
        self.header = FrameHeader(**kwargs)

    @classmethod
    def default(cls, message, from_client = False):
        """
          Construct a basic websocket frame from some default values.
          Creates a non-fragmented text frame.
        """
        if from_client:
            mask_bit = 1
            masking_key = os.urandom(4)
        else:
            mask_bit = 0
            masking_key = None

        return cls(
            message,
            fin = 1, # final frame
            opcode = OPCODE.TEXT, # text
            mask = mask_bit,
            masking_key = masking_key,
        )

    def human_readable(self):
        return "\n".join([
            ("fin                   - " + str(self.header.fin)),
            ("rsv1                  - " + str(self.header.rsv1)),
            ("rsv2                  - " + str(self.header.rsv2)),
            ("rsv3                  - " + str(self.header.rsv3)),
            ("opcode                - " + str(self.header.opcode)),
            ("mask                  - " + str(self.header.mask)),
            ("length_code           - " + str(self.header.length_code)),
            ("masking_key           - " + repr(str(self.header.masking_key))),
            ("payload               - " + repr(str(self.payload))),
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
        b = self.header.to_bytes()
        if self.header.masking_key:
            b += apply_mask(self.payload, self.header.masking_key)
        else:
            b += self.payload
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
        header = FrameHeader.from_file(fp)
        payload = fp.read(header.payload_length)

        if header.mask == 1 and header.masking_key:
            payload = apply_mask(payload, header.masking_key)

        return cls(
            payload,
            fin = header.fin,
            opcode = header.opcode,
            mask = header.mask,
            payload_length = header.payload_length,
            masking_key = header.masking_key,
        )

    def __eq__(self, other):
        return self.to_bytes() == other.to_bytes()
