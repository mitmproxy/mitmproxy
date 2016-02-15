from __future__ import absolute_import
import os
import struct
import io
import warnings

import six

from .protocol import Masker
from netlib import tcp
from netlib import utils


MAX_16_BIT_INT = (1 << 16)
MAX_64_BIT_INT = (1 << 64)

DEFAULT=object()

OPCODE = utils.BiDi(
    CONTINUE=0x00,
    TEXT=0x01,
    BINARY=0x02,
    CLOSE=0x08,
    PING=0x09,
    PONG=0x0a
)


class FrameHeader(object):

    def __init__(
        self,
        opcode=OPCODE.TEXT,
        payload_length=0,
        fin=False,
        rsv1=False,
        rsv2=False,
        rsv3=False,
        masking_key=DEFAULT,
        mask=DEFAULT,
        length_code=DEFAULT
    ):
        if not 0 <= opcode < 2 ** 4:
            raise ValueError("opcode must be 0-16")
        self.opcode = opcode
        self.payload_length = payload_length
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3

        if length_code is DEFAULT:
            self.length_code = self._make_length_code(self.payload_length)
        else:
            self.length_code = length_code

        if mask is DEFAULT and masking_key is DEFAULT:
            self.mask = False
            self.masking_key = b""
        elif mask is DEFAULT:
            self.mask = 1
            self.masking_key = masking_key
        elif masking_key is DEFAULT:
            self.mask = mask
            self.masking_key = os.urandom(4)
        else:
            self.mask = mask
            self.masking_key = masking_key

        if self.masking_key and len(self.masking_key) != 4:
            raise ValueError("Masking key must be 4 bytes.")

    @classmethod
    def _make_length_code(self, length):
        """
         A websockets frame contains an initial length_code, and an optional
         extended length code to represent the actual length if length code is
         larger than 125
        """
        if length <= 125:
            return length
        elif length >= 126 and length <= 65535:
            return 126
        else:
            return 127

    def __repr__(self):
        vals = [
            "ws frame:",
            OPCODE.get_name(self.opcode, hex(self.opcode)).lower()
        ]
        flags = []
        for i in ["fin", "rsv1", "rsv2", "rsv3", "mask"]:
            if getattr(self, i):
                flags.append(i)
        if flags:
            vals.extend([":", "|".join(flags)])
        if self.masking_key:
            vals.append(":key=%s" % repr(self.masking_key))
        if self.payload_length:
            vals.append(" %s" % utils.pretty_size(self.payload_length))
        return "".join(vals)

    def human_readable(self):
        warnings.warn("FrameHeader.to_bytes is deprecated, use bytes(frame_header) instead.", DeprecationWarning)
        return repr(self)

    def __bytes__(self):
        first_byte = utils.setbit(0, 7, self.fin)
        first_byte = utils.setbit(first_byte, 6, self.rsv1)
        first_byte = utils.setbit(first_byte, 5, self.rsv2)
        first_byte = utils.setbit(first_byte, 4, self.rsv3)
        first_byte = first_byte | self.opcode

        second_byte = utils.setbit(self.length_code, 7, self.mask)

        b = six.int2byte(first_byte) + six.int2byte(second_byte)

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
        if self.masking_key:
            b += self.masking_key
        return b

    if six.PY2:
        __str__ = __bytes__

    def to_bytes(self):
        warnings.warn("FrameHeader.to_bytes is deprecated, use bytes(frame_header) instead.", DeprecationWarning)
        return bytes(self)

    @classmethod
    def from_file(cls, fp):
        """
          read a websockets frame header
        """
        first_byte = six.byte2int(fp.safe_read(1))
        second_byte = six.byte2int(fp.safe_read(1))

        fin = utils.getbit(first_byte, 7)
        rsv1 = utils.getbit(first_byte, 6)
        rsv2 = utils.getbit(first_byte, 5)
        rsv3 = utils.getbit(first_byte, 4)
        # grab right-most 4 bits
        opcode = first_byte & 15
        mask_bit = utils.getbit(second_byte, 7)
        # grab the next 7 bits
        length_code = second_byte & 127

        # payload_lengthy > 125 indicates you need to read more bytes
        # to get the actual payload length
        if length_code <= 125:
            payload_length = length_code
        elif length_code == 126:
            payload_length, = struct.unpack("!H", fp.safe_read(2))
        elif length_code == 127:
            payload_length, = struct.unpack("!Q", fp.safe_read(8))

        # masking key only present if mask bit set
        if mask_bit == 1:
            masking_key = fp.safe_read(4)
        else:
            masking_key = None

        return cls(
            fin=fin,
            rsv1=rsv1,
            rsv2=rsv2,
            rsv3=rsv3,
            opcode=opcode,
            mask=mask_bit,
            length_code=length_code,
            payload_length=payload_length,
            masking_key=masking_key,
        )

    def __eq__(self, other):
        if isinstance(other, FrameHeader):
            return bytes(self) == bytes(other)
        return False


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

    def __init__(self, payload=b"", **kwargs):
        self.payload = payload
        kwargs["payload_length"] = kwargs.get("payload_length", len(payload))
        self.header = FrameHeader(**kwargs)

    @classmethod
    def default(cls, message, from_client=False):
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
            fin=1,  # final frame
            opcode=OPCODE.TEXT,  # text
            mask=mask_bit,
            masking_key=masking_key,
        )

    @classmethod
    def from_bytes(cls, bytestring):
        """
          Construct a websocket frame from an in-memory bytestring
          to construct a frame from a stream of bytes, use from_file() directly
        """
        return cls.from_file(tcp.Reader(io.BytesIO(bytestring)))

    def __repr__(self):
        ret = repr(self.header)
        if self.payload:
            ret = ret + "\nPayload:\n" + utils.clean_bin(self.payload).decode("ascii")
        return ret

    def human_readable(self):
        warnings.warn("Frame.to_bytes is deprecated, use bytes(frame) instead.", DeprecationWarning)
        return repr(self)

    def __bytes__(self):
        """
            Serialize the frame to wire format. Returns a string.
        """
        b = bytes(self.header)
        if self.header.masking_key:
            b += Masker(self.header.masking_key)(self.payload)
        else:
            b += self.payload
        return b

    if six.PY2:
        __str__ = __bytes__

    def to_bytes(self):
        warnings.warn("FrameHeader.to_bytes is deprecated, use bytes(frame_header) instead.", DeprecationWarning)
        return bytes(self)

    def to_file(self, writer):
        warnings.warn("Frame.to_file is deprecated, use wfile.write(bytes(frame)) instead.", DeprecationWarning)
        writer.write(bytes(self))
        writer.flush()

    @classmethod
    def from_file(cls, fp):
        """
          read a websockets frame sent by a server or client

          fp is a "file like" object that could be backed by a network
          stream or a disk or an in memory stream reader
        """
        header = FrameHeader.from_file(fp)
        payload = fp.safe_read(header.payload_length)

        if header.mask == 1 and header.masking_key:
            payload = Masker(header.masking_key)(payload)

        return cls(
            payload,
            fin=header.fin,
            opcode=header.opcode,
            mask=header.mask,
            payload_length=header.payload_length,
            masking_key=header.masking_key,
            rsv1=header.rsv1,
            rsv2=header.rsv2,
            rsv3=header.rsv3,
            length_code=header.length_code
        )

    def __eq__(self, other):
        if isinstance(other, Frame):
            return bytes(self) == bytes(other)
        return False
