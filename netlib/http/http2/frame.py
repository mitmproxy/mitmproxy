import sys
import struct
from hpack.hpack import Encoder, Decoder

from .. import utils


class FrameSizeError(Exception):
    pass


class Frame(object):

    """
        Baseclass Frame
        contains header
        payload is defined in subclasses
    """

    FLAG_NO_FLAGS = 0x0
    FLAG_ACK = 0x1
    FLAG_END_STREAM = 0x1
    FLAG_END_HEADERS = 0x4
    FLAG_PADDED = 0x8
    FLAG_PRIORITY = 0x20

    def __init__(
            self,
            state=None,
            length=0,
            flags=FLAG_NO_FLAGS,
            stream_id=0x0):
        valid_flags = reduce(lambda x, y: x | y, self.VALID_FLAGS, 0x0)
        if flags | valid_flags != valid_flags:
            raise ValueError('invalid flags detected.')

        if state is None:
            class State(object):
                pass

            state = State()
            state.http2_settings = HTTP2_DEFAULT_SETTINGS.copy()
            state.encoder = Encoder()
            state.decoder = Decoder()

        self.state = state

        self.length = length
        self.type = self.TYPE
        self.flags = flags
        self.stream_id = stream_id

    @classmethod
    def _check_frame_size(cls, length, state):
        if state:
            settings = state.http2_settings
        else:
            settings = HTTP2_DEFAULT_SETTINGS.copy()

        max_frame_size = settings[
            SettingsFrame.SETTINGS.SETTINGS_MAX_FRAME_SIZE]

        if length > max_frame_size:
            raise FrameSizeError(
                "Frame size exceeded: %d, but only %d allowed." % (
                    length, max_frame_size))

    @classmethod
    def from_file(cls, fp, state=None):
        """
          read a HTTP/2 frame sent by a server or client
          fp is a "file like" object that could be backed by a network
          stream or a disk or an in memory stream reader
        """
        raw_header = fp.safe_read(9)

        fields = struct.unpack("!HBBBL", raw_header)
        length = (fields[0] << 8) + fields[1]
        flags = fields[3]
        stream_id = fields[4]

        if raw_header[:4] == b'HTTP':  # pragma no cover
            print >> sys.stderr, "WARNING: This looks like an HTTP/1 connection!"

        cls._check_frame_size(length, state)

        payload = fp.safe_read(length)
        return FRAMES[fields[2]].from_bytes(
            state,
            length,
            flags,
            stream_id,
            payload)

    def to_bytes(self):
        payload = self.payload_bytes()
        self.length = len(payload)

        self._check_frame_size(self.length, self.state)

        b = struct.pack('!HB', self.length & 0xFFFF00, self.length & 0x0000FF)
        b += struct.pack('!B', self.TYPE)
        b += struct.pack('!B', self.flags)
        b += struct.pack('!L', self.stream_id & 0x7FFFFFFF)
        b += payload

        return b

    def payload_bytes(self):  # pragma: no cover
        raise NotImplementedError()

    def payload_human_readable(self):  # pragma: no cover
        raise NotImplementedError()

    def human_readable(self, direction="-"):
        self.length = len(self.payload_bytes())

        return "\n".join([
            "%s: %s | length: %d | flags: %#x | stream_id: %d" % (
                direction, self.__class__.__name__, self.length, self.flags, self.stream_id),
            self.payload_human_readable(),
            "===============================================================",
        ])

    def __eq__(self, other):
        return self.to_bytes() == other.to_bytes()


class DataFrame(Frame):
    TYPE = 0x0
    VALID_FLAGS = [Frame.FLAG_END_STREAM, Frame.FLAG_PADDED]

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            payload=b'',
            pad_length=0):
        super(DataFrame, self).__init__(state, length, flags, stream_id)
        self.payload = payload
        self.pad_length = pad_length

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        if f.flags & Frame.FLAG_PADDED:
            f.pad_length = struct.unpack('!B', payload[0])[0]
            f.payload = payload[1:-f.pad_length]
        else:
            f.payload = payload

        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError('DATA frames MUST be associated with a stream.')

        b = b''
        if self.flags & self.FLAG_PADDED:
            b += struct.pack('!B', self.pad_length)

        b += bytes(self.payload)

        if self.flags & self.FLAG_PADDED:
            b += b'\0' * self.pad_length

        return b

    def payload_human_readable(self):
        return "payload: %s" % str(self.payload)


class HeadersFrame(Frame):
    TYPE = 0x1
    VALID_FLAGS = [
        Frame.FLAG_END_STREAM,
        Frame.FLAG_END_HEADERS,
        Frame.FLAG_PADDED,
        Frame.FLAG_PRIORITY]

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            header_block_fragment=b'',
            pad_length=0,
            exclusive=False,
            stream_dependency=0x0,
            weight=0):
        super(HeadersFrame, self).__init__(state, length, flags, stream_id)

        self.header_block_fragment = header_block_fragment
        self.pad_length = pad_length
        self.exclusive = exclusive
        self.stream_dependency = stream_dependency
        self.weight = weight

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        if f.flags & Frame.FLAG_PADDED:
            f.pad_length = struct.unpack('!B', payload[0])[0]
            f.header_block_fragment = payload[1:-f.pad_length]
        else:
            f.header_block_fragment = payload[0:]

        if f.flags & Frame.FLAG_PRIORITY:
            f.stream_dependency, f.weight = struct.unpack(
                '!LB', f.header_block_fragment[:5])
            f.exclusive = bool(f.stream_dependency >> 31)
            f.stream_dependency &= 0x7FFFFFFF
            f.header_block_fragment = f.header_block_fragment[5:]

        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError('HEADERS frames MUST be associated with a stream.')

        b = b''
        if self.flags & self.FLAG_PADDED:
            b += struct.pack('!B', self.pad_length)

        if self.flags & self.FLAG_PRIORITY:
            b += struct.pack('!LB',
                             (int(self.exclusive) << 31) | self.stream_dependency,
                             self.weight)

        b += self.header_block_fragment

        if self.flags & self.FLAG_PADDED:
            b += b'\0' * self.pad_length

        return b

    def payload_human_readable(self):
        s = []

        if self.flags & self.FLAG_PRIORITY:
            s.append("exclusive: %d" % self.exclusive)
            s.append("stream dependency: %#x" % self.stream_dependency)
            s.append("weight: %d" % self.weight)

        if self.flags & self.FLAG_PADDED:
            s.append("padding: %d" % self.pad_length)

        s.append(
            "header_block_fragment: %s" %
            self.header_block_fragment.encode('hex'))

        return "\n".join(s)


class PriorityFrame(Frame):
    TYPE = 0x2
    VALID_FLAGS = []

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            exclusive=False,
            stream_dependency=0x0,
            weight=0):
        super(PriorityFrame, self).__init__(state, length, flags, stream_id)
        self.exclusive = exclusive
        self.stream_dependency = stream_dependency
        self.weight = weight

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        f.stream_dependency, f.weight = struct.unpack('!LB', payload)
        f.exclusive = bool(f.stream_dependency >> 31)
        f.stream_dependency &= 0x7FFFFFFF

        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError(
                'PRIORITY frames MUST be associated with a stream.')

        if self.stream_dependency == 0x0:
            raise ValueError('stream dependency is invalid.')

        return struct.pack(
            '!LB',
            (int(
                self.exclusive) << 31) | self.stream_dependency,
            self.weight)

    def payload_human_readable(self):
        s = []
        s.append("exclusive: %d" % self.exclusive)
        s.append("stream dependency: %#x" % self.stream_dependency)
        s.append("weight: %d" % self.weight)
        return "\n".join(s)


class RstStreamFrame(Frame):
    TYPE = 0x3
    VALID_FLAGS = []

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            error_code=0x0):
        super(RstStreamFrame, self).__init__(state, length, flags, stream_id)
        self.error_code = error_code

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)
        f.error_code = struct.unpack('!L', payload)[0]
        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError(
                'RST_STREAM frames MUST be associated with a stream.')

        return struct.pack('!L', self.error_code)

    def payload_human_readable(self):
        return "error code: %#x" % self.error_code


class SettingsFrame(Frame):
    TYPE = 0x4
    VALID_FLAGS = [Frame.FLAG_ACK]

    SETTINGS = utils.BiDi(
        SETTINGS_HEADER_TABLE_SIZE=0x1,
        SETTINGS_ENABLE_PUSH=0x2,
        SETTINGS_MAX_CONCURRENT_STREAMS=0x3,
        SETTINGS_INITIAL_WINDOW_SIZE=0x4,
        SETTINGS_MAX_FRAME_SIZE=0x5,
        SETTINGS_MAX_HEADER_LIST_SIZE=0x6,
    )

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            settings=None):
        super(SettingsFrame, self).__init__(state, length, flags, stream_id)

        if settings is None:
            settings = {}

        self.settings = settings

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        for i in xrange(0, len(payload), 6):
            identifier, value = struct.unpack("!HL", payload[i:i + 6])
            f.settings[identifier] = value

        return f

    def payload_bytes(self):
        if self.stream_id != 0x0:
            raise ValueError(
                'SETTINGS frames MUST NOT be associated with a stream.')

        b = b''
        for identifier, value in self.settings.items():
            b += struct.pack("!HL", identifier & 0xFF, value)

        return b

    def payload_human_readable(self):
        s = []

        for identifier, value in self.settings.items():
            s.append("%s: %#x" % (self.SETTINGS.get_name(identifier), value))

        if not s:
            return "settings: None"
        else:
            return "\n".join(s)


class PushPromiseFrame(Frame):
    TYPE = 0x5
    VALID_FLAGS = [Frame.FLAG_END_HEADERS, Frame.FLAG_PADDED]

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            promised_stream=0x0,
            header_block_fragment=b'',
            pad_length=0):
        super(PushPromiseFrame, self).__init__(state, length, flags, stream_id)
        self.pad_length = pad_length
        self.promised_stream = promised_stream
        self.header_block_fragment = header_block_fragment

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        if f.flags & Frame.FLAG_PADDED:
            f.pad_length, f.promised_stream = struct.unpack('!BL', payload[:5])
            f.header_block_fragment = payload[5:-f.pad_length]
        else:
            f.promised_stream = int(struct.unpack("!L", payload[:4])[0])
            f.header_block_fragment = payload[4:]

        f.promised_stream &= 0x7FFFFFFF

        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError(
                'PUSH_PROMISE frames MUST be associated with a stream.')

        if self.promised_stream == 0x0:
            raise ValueError('Promised stream id not valid.')

        b = b''
        if self.flags & self.FLAG_PADDED:
            b += struct.pack('!B', self.pad_length)

        b += struct.pack('!L', self.promised_stream & 0x7FFFFFFF)
        b += bytes(self.header_block_fragment)

        if self.flags & self.FLAG_PADDED:
            b += b'\0' * self.pad_length

        return b

    def payload_human_readable(self):
        s = []

        if self.flags & self.FLAG_PADDED:
            s.append("padding: %d" % self.pad_length)

        s.append("promised stream: %#x" % self.promised_stream)
        s.append(
            "header_block_fragment: %s" %
            self.header_block_fragment.encode('hex'))

        return "\n".join(s)


class PingFrame(Frame):
    TYPE = 0x6
    VALID_FLAGS = [Frame.FLAG_ACK]

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            payload=b''):
        super(PingFrame, self).__init__(state, length, flags, stream_id)
        self.payload = payload

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)
        f.payload = payload
        return f

    def payload_bytes(self):
        if self.stream_id != 0x0:
            raise ValueError(
                'PING frames MUST NOT be associated with a stream.')

        b = self.payload[0:8]
        b += b'\0' * (8 - len(b))
        return b

    def payload_human_readable(self):
        return "opaque data: %s" % str(self.payload)


class GoAwayFrame(Frame):
    TYPE = 0x7
    VALID_FLAGS = []

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            last_stream=0x0,
            error_code=0x0,
            data=b''):
        super(GoAwayFrame, self).__init__(state, length, flags, stream_id)
        self.last_stream = last_stream
        self.error_code = error_code
        self.data = data

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        f.last_stream, f.error_code = struct.unpack("!LL", payload[:8])
        f.last_stream &= 0x7FFFFFFF
        f.data = payload[8:]

        return f

    def payload_bytes(self):
        if self.stream_id != 0x0:
            raise ValueError(
                'GOAWAY frames MUST NOT be associated with a stream.')

        b = struct.pack('!LL', self.last_stream & 0x7FFFFFFF, self.error_code)
        b += bytes(self.data)
        return b

    def payload_human_readable(self):
        s = []
        s.append("last stream: %#x" % self.last_stream)
        s.append("error code: %d" % self.error_code)
        s.append("debug data: %s" % str(self.data))
        return "\n".join(s)


class WindowUpdateFrame(Frame):
    TYPE = 0x8
    VALID_FLAGS = []

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            window_size_increment=0x0):
        super(WindowUpdateFrame, self).__init__(state, length, flags, stream_id)
        self.window_size_increment = window_size_increment

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)

        f.window_size_increment = struct.unpack("!L", payload)[0]
        f.window_size_increment &= 0x7FFFFFFF

        return f

    def payload_bytes(self):
        if self.window_size_increment <= 0 or self.window_size_increment >= 2 ** 31:
            raise ValueError(
                'Window Szie Increment MUST be greater than 0 and less than 2^31.')

        return struct.pack('!L', self.window_size_increment & 0x7FFFFFFF)

    def payload_human_readable(self):
        return "window size increment: %#x" % self.window_size_increment


class ContinuationFrame(Frame):
    TYPE = 0x9
    VALID_FLAGS = [Frame.FLAG_END_HEADERS]

    def __init__(
            self,
            state=None,
            length=0,
            flags=Frame.FLAG_NO_FLAGS,
            stream_id=0x0,
            header_block_fragment=b''):
        super(ContinuationFrame, self).__init__(state, length, flags, stream_id)
        self.header_block_fragment = header_block_fragment

    @classmethod
    def from_bytes(cls, state, length, flags, stream_id, payload):
        f = cls(state=state, length=length, flags=flags, stream_id=stream_id)
        f.header_block_fragment = payload
        return f

    def payload_bytes(self):
        if self.stream_id == 0x0:
            raise ValueError(
                'CONTINUATION frames MUST be associated with a stream.')

        return self.header_block_fragment

    def payload_human_readable(self):
        s = []
        s.append(
            "header_block_fragment: %s" %
            self.header_block_fragment.encode('hex'))
        return "\n".join(s)

_FRAME_CLASSES = [
    DataFrame,
    HeadersFrame,
    PriorityFrame,
    RstStreamFrame,
    SettingsFrame,
    PushPromiseFrame,
    PingFrame,
    GoAwayFrame,
    WindowUpdateFrame,
    ContinuationFrame
]
FRAMES = {cls.TYPE: cls for cls in _FRAME_CLASSES}


HTTP2_DEFAULT_SETTINGS = {
    SettingsFrame.SETTINGS.SETTINGS_HEADER_TABLE_SIZE: 4096,
    SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 1,
    SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS: None,
    SettingsFrame.SETTINGS.SETTINGS_INITIAL_WINDOW_SIZE: 2 ** 16 - 1,
    SettingsFrame.SETTINGS.SETTINGS_MAX_FRAME_SIZE: 2 ** 14,
    SettingsFrame.SETTINGS.SETTINGS_MAX_HEADER_LIST_SIZE: None,
}
