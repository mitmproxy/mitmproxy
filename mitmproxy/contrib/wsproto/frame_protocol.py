# -*- coding: utf-8 -*-
"""
wsproto/frame_protocol
~~~~~~~~~~~~~~

WebSocket frame protocol implementation.
"""

import os
import itertools
import struct
from codecs import getincrementaldecoder
from collections import namedtuple

from enum import Enum, IntEnum

from .compat import unicode, Utf8Validator

try:
    from wsaccel.xormask import XorMaskerSimple
except ImportError:
    class XorMaskerSimple:
        def __init__(self, masking_key):
            self._maskbytes = itertools.cycle(bytearray(masking_key))

        def process(self, data):
            maskbytes = self._maskbytes
            return bytearray(b ^ next(maskbytes) for b in bytearray(data))


class XorMaskerNull:
    def process(self, data):
        return data


# RFC6455, Section 5.2 - Base Framing Protocol

# Payload length constants
PAYLOAD_LENGTH_TWO_BYTE = 126
PAYLOAD_LENGTH_EIGHT_BYTE = 127
MAX_PAYLOAD_NORMAL = 125
MAX_PAYLOAD_TWO_BYTE = 2 ** 16 - 1
MAX_PAYLOAD_EIGHT_BYTE = 2 ** 64 - 1
MAX_FRAME_PAYLOAD = MAX_PAYLOAD_EIGHT_BYTE

# MASK and PAYLOAD LEN are packed into a byte
MASK_MASK = 0x80
PAYLOAD_LEN_MASK = 0x7f

# FIN, RSV[123] and OPCODE are packed into a single byte
FIN_MASK = 0x80
RSV1_MASK = 0x40
RSV2_MASK = 0x20
RSV3_MASK = 0x10
OPCODE_MASK = 0x0f


class Opcode(IntEnum):
    """
    RFC 6455, Section 5.2 - Base Framing Protocol
    """
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

    def iscontrol(self):
        return bool(self & 0x08)


class CloseReason(IntEnum):
    """
    RFC 6455, Section 7.4.1 - Defined Status Codes
    """
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS_RCVD = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_FRAME_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXT = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    TLS_HANDSHAKE_FAILED = 1015


# RFC 6455, Section 7.4.1 - Defined Status Codes
LOCAL_ONLY_CLOSE_REASONS = (
    CloseReason.NO_STATUS_RCVD,
    CloseReason.ABNORMAL_CLOSURE,
    CloseReason.TLS_HANDSHAKE_FAILED,
)


# RFC 6455, Section 7.4.2 - Status Code Ranges
MIN_CLOSE_REASON = 1000
MIN_PROTOCOL_CLOSE_REASON = 1000
MAX_PROTOCOL_CLOSE_REASON = 2999
MIN_LIBRARY_CLOSE_REASON = 3000
MAX_LIBRARY_CLOSE_REASON = 3999
MIN_PRIVATE_CLOSE_REASON = 4000
MAX_PRIVATE_CLOSE_REASON = 4999
MAX_CLOSE_REASON = 4999


NULL_MASK = struct.pack("!I", 0)


class ParseFailed(Exception):
    def __init__(self, msg, code=CloseReason.PROTOCOL_ERROR):
        super(ParseFailed, self).__init__(msg)
        self.code = code


Header = namedtuple("Header", "fin rsv opcode payload_len masking_key".split())


Frame = namedtuple("Frame",
                   "opcode payload frame_finished message_finished".split())


RsvBits = namedtuple("RsvBits", "rsv1 rsv2 rsv3".split())


def _truncate_utf8(data, nbytes):
    if len(data) <= nbytes:
        return data

    # Truncate
    data = data[:nbytes]
    # But we might have cut a codepoint in half, in which case we want to
    # discard the partial character so the data is at least
    # well-formed. This is a little inefficient since it processes the
    # whole message twice when in theory we could just peek at the last
    # few characters, but since this is only used for close messages (max
    # length = 125 bytes) it really doesn't matter.
    data = data.decode("utf-8", errors="ignore").encode("utf-8")
    return data


class Buffer(object):
    def __init__(self, initial_bytes=None):
        self.buffer = bytearray()
        self.bytes_used = 0
        if initial_bytes:
            self.feed(initial_bytes)

    def feed(self, new_bytes):
        self.buffer += new_bytes

    def consume_at_most(self, nbytes):
        if not nbytes:
            return bytearray()

        data = self.buffer[self.bytes_used:self.bytes_used + nbytes]
        self.bytes_used += len(data)
        return data

    def consume_exactly(self, nbytes):
        if len(self.buffer) - self.bytes_used < nbytes:
            return None

        return self.consume_at_most(nbytes)

    def commit(self):
        # In CPython 3.4+, del[:n] is amortized O(n), *not* quadratic
        del self.buffer[:self.bytes_used]
        self.bytes_used = 0

    def rollback(self):
        self.bytes_used = 0

    def __len__(self):
        return len(self.buffer)


class MessageDecoder(object):
    def __init__(self):
        self.opcode = None
        self.validator = None
        self.decoder = None

    def process_frame(self, frame):
        assert not frame.opcode.iscontrol()

        if self.opcode is None:
            if frame.opcode is Opcode.CONTINUATION:
                raise ParseFailed("unexpected CONTINUATION")
            self.opcode = frame.opcode
        elif frame.opcode is not Opcode.CONTINUATION:
            raise ParseFailed("expected CONTINUATION, got %r" % frame.opcode)

        if frame.opcode is Opcode.TEXT:
            self.validator = Utf8Validator()
            self.decoder = getincrementaldecoder("utf-8")()

        finished = frame.frame_finished and frame.message_finished

        if self.decoder is not None:
            data = self.decode_payload(frame.payload, finished)
        else:
            data = frame.payload

        frame = Frame(self.opcode, data, frame.frame_finished, finished)

        if finished:
            self.opcode = None
            self.decoder = None

        return frame

    def decode_payload(self, data, finished):
        if self.validator is not None:
            results = self.validator.validate(bytes(data))
            if not results[0] or (finished and not results[1]):
                raise ParseFailed(u'encountered invalid UTF-8 while processing'
                                  ' text message at payload octet index %d' %
                                  results[3],
                                  CloseReason.INVALID_FRAME_PAYLOAD_DATA)

        try:
            return self.decoder.decode(data, finished)
        except UnicodeDecodeError as exc:
            raise ParseFailed(str(exc), CloseReason.INVALID_FRAME_PAYLOAD_DATA)


class FrameDecoder(object):
    def __init__(self, client, extensions=None):
        self.client = client
        self.extensions = extensions or []

        self.buffer = Buffer()

        self.header = None
        self.effective_opcode = None
        self.masker = None
        self.payload_required = 0
        self.payload_consumed = 0

    def receive_bytes(self, data):
        self.buffer.feed(data)

    def process_buffer(self):
        if not self.header:
            if not self.parse_header():
                return None

        if len(self.buffer) < self.payload_required:
            return None

        payload_remaining = self.header.payload_len - self.payload_consumed
        payload = self.buffer.consume_at_most(payload_remaining)
        if not payload and self.header.payload_len > 0:
            return None
        self.buffer.commit()

        self.payload_consumed += len(payload)
        finished = self.payload_consumed == self.header.payload_len

        payload = self.masker.process(payload)

        for extension in self.extensions:
            payload = extension.frame_inbound_payload_data(self, payload)
            if isinstance(payload, CloseReason):
                raise ParseFailed("error in extension", payload)

        if finished:
            final = bytearray()
            for extension in self.extensions:
                result = extension.frame_inbound_complete(self,
                                                          self.header.fin)
                if isinstance(result, CloseReason):
                    raise ParseFailed("error in extension", result)
                if result is not None:
                    final += result
            payload += final

        frame = Frame(self.effective_opcode, payload, finished,
                      self.header.fin)

        if finished:
            self.header = None
            self.effective_opcode = None
            self.masker = None
        else:
            self.effective_opcode = Opcode.CONTINUATION

        return frame

    def parse_header(self):
        data = self.buffer.consume_exactly(2)
        if data is None:
            self.buffer.rollback()
            return False

        fin = bool(data[0] & FIN_MASK)
        rsv = RsvBits(bool(data[0] & RSV1_MASK),
                      bool(data[0] & RSV2_MASK),
                      bool(data[0] & RSV3_MASK))
        opcode = data[0] & OPCODE_MASK
        try:
            opcode = Opcode(opcode)
        except ValueError:
            raise ParseFailed("Invalid opcode {:#x}".format(opcode))

        if opcode.iscontrol() and not fin:
            raise ParseFailed("Invalid attempt to fragment control frame")

        has_mask = bool(data[1] & MASK_MASK)
        payload_len = data[1] & PAYLOAD_LEN_MASK
        payload_len = self.parse_extended_payload_length(opcode, payload_len)
        if payload_len is None:
            self.buffer.rollback()
            return False

        self.extension_processing(opcode, rsv, payload_len)

        if has_mask and self.client:
            raise ParseFailed("client received unexpected masked frame")
        if not has_mask and not self.client:
            raise ParseFailed("server received unexpected unmasked frame")
        if has_mask:
            masking_key = self.buffer.consume_exactly(4)
            if masking_key is None:
                self.buffer.rollback()
                return False
            self.masker = XorMaskerSimple(masking_key)
        else:
            self.masker = XorMaskerNull()

        self.buffer.commit()
        self.header = Header(fin, rsv, opcode, payload_len, None)
        self.effective_opcode = self.header.opcode
        if self.header.opcode.iscontrol():
            self.payload_required = payload_len
        else:
            self.payload_required = 0
        self.payload_consumed = 0
        return True

    def parse_extended_payload_length(self, opcode, payload_len):
        if opcode.iscontrol() and payload_len > MAX_PAYLOAD_NORMAL:
            raise ParseFailed("Control frame with payload len > 125")
        if payload_len == PAYLOAD_LENGTH_TWO_BYTE:
            data = self.buffer.consume_exactly(2)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!H", data)
            if payload_len <= MAX_PAYLOAD_NORMAL:
                raise ParseFailed(
                    "Payload length used 2 bytes when 1 would have sufficed")
        elif payload_len == PAYLOAD_LENGTH_EIGHT_BYTE:
            data = self.buffer.consume_exactly(8)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!Q", data)
            if payload_len <= MAX_PAYLOAD_TWO_BYTE:
                raise ParseFailed(
                    "Payload length used 8 bytes when 2 would have sufficed")
            if payload_len >> 63:
                # I'm not sure why this is illegal, but that's what the RFC
                # says, so...
                raise ParseFailed("8-byte payload length with non-zero MSB")

        return payload_len

    def extension_processing(self, opcode, rsv, payload_len):
        rsv_used = [False, False, False]
        for extension in self.extensions:
            result = extension.frame_inbound_header(self, opcode, rsv,
                                                    payload_len)
            if isinstance(result, CloseReason):
                raise ParseFailed("error in extension", result)
            for bit, used in enumerate(result):
                if used:
                    rsv_used[bit] = True
        for expected, found in zip(rsv_used, rsv):
            if found and not expected:
                raise ParseFailed("Reserved bit set unexpectedly")


class FrameProtocol(object):
    class State(Enum):
        HEADER = 1
        PAYLOAD = 2
        FRAME_COMPLETE = 3
        FAILED = 4

    def __init__(self, client, extensions):
        self.client = client
        self.extensions = [ext for ext in extensions if ext.enabled()]

        # Global state
        self._frame_decoder = FrameDecoder(self.client, self.extensions)
        self._message_decoder = MessageDecoder()
        self._parse_more = self.parse_more_gen()

        self._outbound_opcode = None

    def _process_close(self, frame):
        data = frame.payload

        if not data:
            # "If this Close control frame contains no status code, _The
            # WebSocket Connection Close Code_ is considered to be 1005"
            data = (CloseReason.NO_STATUS_RCVD, "")
        elif len(data) == 1:
            raise ParseFailed("CLOSE with 1 byte payload")
        else:
            (code,) = struct.unpack("!H", data[:2])
            if code < MIN_CLOSE_REASON or code > MAX_CLOSE_REASON:
                raise ParseFailed("CLOSE with invalid code")
            try:
                code = CloseReason(code)
            except ValueError:
                pass
            if code in LOCAL_ONLY_CLOSE_REASONS:
                raise ParseFailed(
                    "remote CLOSE with local-only reason")
            if not isinstance(code, CloseReason) and \
               code <= MAX_PROTOCOL_CLOSE_REASON:
                raise ParseFailed(
                    "CLOSE with unknown reserved code")
            validator = Utf8Validator()
            if validator is not None:
                results = validator.validate(bytes(data[2:]))
                if not (results[0] and results[1]):
                    raise ParseFailed(u'encountered invalid UTF-8 while'
                                      ' processing close message at payload'
                                      ' octet index %d' %
                                      results[3],
                                      CloseReason.INVALID_FRAME_PAYLOAD_DATA)
            try:
                reason = data[2:].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ParseFailed(
                    "Error decoding CLOSE reason: " + str(exc),
                    CloseReason.INVALID_FRAME_PAYLOAD_DATA)
            data = (code, reason)

        return Frame(frame.opcode, data, frame.frame_finished,
                     frame.message_finished)

    def parse_more_gen(self):
        # Consume as much as we can from self._buffer, yielding events, and
        # then yield None when we need more data. Or raise ParseFailed.

        # XX FIXME this should probably be refactored so that we never see
        # disabled extensions in the first place...
        self.extensions = [ext for ext in self.extensions if ext.enabled()]
        closed = False

        while not closed:
            frame = self._frame_decoder.process_buffer()

            if frame is not None:
                if not frame.opcode.iscontrol():
                    frame = self._message_decoder.process_frame(frame)
                elif frame.opcode == Opcode.CLOSE:
                    frame = self._process_close(frame)
                    closed = True

            yield frame

    def receive_bytes(self, data):
        self._frame_decoder.receive_bytes(data)

    def received_frames(self):
        for event in self._parse_more:
            if event is None:
                break
            else:
                yield event

    def close(self, code=None, reason=None):
        payload = bytearray()
        if code is None and reason is not None:
            raise TypeError("cannot specify a reason without a code")
        if code in LOCAL_ONLY_CLOSE_REASONS:
            code = CloseReason.NORMAL_CLOSURE
        if code is not None:
            payload += bytearray(struct.pack('!H', code))
            if reason is not None:
                payload += _truncate_utf8(reason.encode('utf-8'),
                                          MAX_PAYLOAD_NORMAL - 2)

        return self._serialize_frame(Opcode.CLOSE, payload)

    def ping(self, payload=b''):
        return self._serialize_frame(Opcode.PING, payload)

    def pong(self, payload=b''):
        return self._serialize_frame(Opcode.PONG, payload)

    def send_data(self, payload=b'', fin=True):
        if isinstance(payload, (bytes, bytearray, memoryview)):
            opcode = Opcode.BINARY
        elif isinstance(payload, unicode):
            opcode = Opcode.TEXT
            payload = payload.encode('utf-8')
        else:
            raise ValueError('Must provide bytes or text')

        if self._outbound_opcode is None:
            self._outbound_opcode = opcode
        elif self._outbound_opcode is not opcode:
            raise TypeError('Data type mismatch inside message')
        else:
            opcode = Opcode.CONTINUATION

        if fin:
            self._outbound_opcode = None

        return self._serialize_frame(opcode, payload, fin)

    def _make_fin_rsv_opcode(self, fin, rsv, opcode):
        fin = int(fin) << 7
        rsv = (int(rsv.rsv1) << 6) + (int(rsv.rsv2) << 5) + \
            (int(rsv.rsv3) << 4)
        opcode = int(opcode)

        return fin | rsv | opcode

    def _serialize_frame(self, opcode, payload=b'', fin=True):
        rsv = RsvBits(False, False, False)
        for extension in reversed(self.extensions):
            rsv, payload = extension.frame_outbound(self, opcode, rsv, payload,
                                                    fin)

        fin_rsv_opcode = self._make_fin_rsv_opcode(fin, rsv, opcode)

        payload_length = len(payload)
        quad_payload = False
        if payload_length <= MAX_PAYLOAD_NORMAL:
            first_payload = payload_length
            second_payload = None
        elif payload_length <= MAX_PAYLOAD_TWO_BYTE:
            first_payload = PAYLOAD_LENGTH_TWO_BYTE
            second_payload = payload_length
        else:
            first_payload = PAYLOAD_LENGTH_EIGHT_BYTE
            second_payload = payload_length
            quad_payload = True

        if self.client:
            first_payload |= 1 << 7

        header = bytearray([fin_rsv_opcode, first_payload])
        if second_payload is not None:
            if opcode.iscontrol():
                raise ValueError("payload too long for control frame")
            if quad_payload:
                header += bytearray(struct.pack('!Q', second_payload))
            else:
                header += bytearray(struct.pack('!H', second_payload))

        if self.client:
            # "The masking key is a 32-bit value chosen at random by the
            # client.  When preparing a masked frame, the client MUST pick a
            # fresh masking key from the set of allowed 32-bit values.  The
            # masking key needs to be unpredictable; thus, the masking key
            # MUST be derived from a strong source of entropy, and the masking
            # key for a given frame MUST NOT make it simple for a server/proxy
            # to predict the masking key for a subsequent frame.  The
            # unpredictability of the masking key is essential to prevent
            # authors of malicious applications from selecting the bytes that
            # appear on the wire."
            #   -- https://tools.ietf.org/html/rfc6455#section-5.3
            masking_key = os.urandom(4)
            masker = XorMaskerSimple(masking_key)
            return header + masking_key + masker.process(payload)

        return header + payload
