import os
import struct
import io

from mitmproxy.net import tcp
from mitmproxy.utils import strutils
from mitmproxy.utils import bits
from mitmproxy.utils import human
from mitmproxy.types import bidi
from .masker import Masker


MAX_16_BIT_INT = (1 << 16)
MAX_64_BIT_INT = (1 << 64)

DEFAULT = object()

# RFC 6455, Section 5.2 - Base Framing Protocol
OPCODE = bidi.BiDi(
    CONTINUE=0x00,
    TEXT=0x01,
    BINARY=0x02,
    CLOSE=0x08,
    PING=0x09,
    PONG=0x0a
)

# RFC 6455, Section 7.4.1 - Defined Status Codes
CLOSE_REASON = bidi.BiDi(
    NORMAL_CLOSURE=1000,
    GOING_AWAY=1001,
    PROTOCOL_ERROR=1002,
    UNSUPPORTED_DATA=1003,
    RESERVED=1004,
    RESERVED_NO_STATUS=1005,
    RESERVED_ABNORMAL_CLOSURE=1006,
    INVALID_PAYLOAD_DATA=1007,
    POLICY_VIOLATION=1008,
    MESSAGE_TOO_BIG=1009,
    MANDATORY_EXTENSION=1010,
    INTERNAL_ERROR=1011,
    RESERVED_TLS_HANDHSAKE_FAILED=1015,
)


class FrameHeader:

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
         A WebSocket frame contains an initial length_code, and an optional
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
            vals.append(" %s" % human.pretty_size(self.payload_length))
        return "".join(vals)

    def __bytes__(self):
        first_byte = bits.setbit(0, 7, self.fin)
        first_byte = bits.setbit(first_byte, 6, self.rsv1)
        first_byte = bits.setbit(first_byte, 5, self.rsv2)
        first_byte = bits.setbit(first_byte, 4, self.rsv3)
        first_byte = first_byte | self.opcode

        second_byte = bits.setbit(self.length_code, 7, self.mask)

        b = bytes([first_byte, second_byte])

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
        else:
            raise ValueError("Payload length exceeds 64bit integer")

        if self.masking_key:
            b += self.masking_key
        return b

    @classmethod
    def from_file(cls, fp):
        """
          read a WebSocket frame header
        """
        first_byte, second_byte = fp.safe_read(2)
        fin = bits.getbit(first_byte, 7)
        rsv1 = bits.getbit(first_byte, 6)
        rsv2 = bits.getbit(first_byte, 5)
        rsv3 = bits.getbit(first_byte, 4)
        opcode = first_byte & 0xF
        mask_bit = bits.getbit(second_byte, 7)
        length_code = second_byte & 0x7F

        # payload_length > 125 indicates you need to read more bytes
        # to get the actual payload length
        if length_code <= 125:
            payload_length = length_code
        elif length_code == 126:
            payload_length, = struct.unpack("!H", fp.safe_read(2))
        else:  # length_code == 127:
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


class Frame:
    """
    Represents a single WebSocket frame.
    Constructor takes human readable forms of the frame components.
    from_bytes() reads from a file-like object to create a new Frame.

    WebSocket frame as defined in RFC6455

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
    def from_bytes(cls, bytestring):
        """
          Construct a websocket frame from an in-memory bytestring
          to construct a frame from a stream of bytes, use from_file() directly
        """
        return cls.from_file(tcp.Reader(io.BytesIO(bytestring)))

    def __repr__(self):
        ret = repr(self.header)
        if self.payload:
            ret = ret + "\nPayload:\n" + strutils.bytes_to_escaped_str(self.payload)
        return ret

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

    @classmethod
    def from_file(cls, fp):
        """
          read a WebSocket frame sent by a server or client

          fp is a "file like" object that could be backed by a network
          stream or a disk or an in memory stream reader
        """
        header = FrameHeader.from_file(fp)
        payload = fp.safe_read(header.payload_length)

        if header.mask == 1 and header.masking_key:
            payload = Masker(header.masking_key)(payload)

        frame = cls(payload)
        frame.header = header
        return frame

    def __eq__(self, other):
        if isinstance(other, Frame):
            return bytes(self) == bytes(other)
        return False
