from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field

import pylsqpack
from aioquic.buffer import Buffer
from aioquic.buffer import BufferReadError
from aioquic.h3.connection import parse_settings
from aioquic.h3.connection import Setting

from ..proxy.layers.http import is_h3_alpn
from mitmproxy import tcp
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy_rs.contentviews import hex_dump


@dataclass(frozen=True)
class Frame:
    """Representation of an HTTP/3 frame."""

    type: int
    data: bytes

    def pretty(self) -> str:
        frame_name = f"0x{self.type:x} Frame"
        if self.type == 0:
            frame_name = "DATA Frame"
        elif self.type == 1:
            try:
                hdrs = pylsqpack.Decoder(4096, 16).feed_header(0, self.data)[1]
                return f"HEADERS Frame\n" + "\n".join(
                    f"{k.decode(errors='backslashreplace')}: {v.decode(errors='backslashreplace')}"
                    for k, v in hdrs
                )
            except Exception as e:
                frame_name = f"HEADERS Frame (error: {e})"
        elif self.type == 4:
            settings = []
            try:
                s = parse_settings(self.data)
            except Exception as e:
                frame_name = f"SETTINGS Frame (error: {e})"
            else:
                for k, v in s.items():
                    try:
                        key = Setting(k).name
                    except ValueError:
                        key = f"0x{k:x}"
                    settings.append(f"{key}: 0x{v:x}")
                return "SETTINGS Frame\n" + "\n".join(settings)
        return f"{frame_name}\n" + hex_dump.prettify(self.data, Metadata())


@dataclass(frozen=True)
class StreamType:
    """Representation of an HTTP/3 stream types."""

    type: int

    def pretty(self) -> str:
        stream_type = {
            0x00: "Control Stream",
            0x01: "Push Stream",
            0x02: "QPACK Encoder Stream",
            0x03: "QPACK Decoder Stream",
        }.get(self.type, f"0x{self.type:x} Stream")
        return stream_type


@dataclass
class ConnectionState:
    message_count: int = 0
    frames: dict[int, list[Frame | StreamType]] = field(default_factory=dict)
    client_buf: bytearray = field(default_factory=bytearray)
    server_buf: bytearray = field(default_factory=bytearray)


class Http3Contentview(Contentview):
    def __init__(self) -> None:
        self.connections: defaultdict[tcp.TCPFlow, ConnectionState] = defaultdict(
            ConnectionState
        )

    @property
    def name(self) -> str:
        return "HTTP/3 Frames"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        flow = metadata.flow
        tcp_message = metadata.tcp_message
        assert isinstance(flow, tcp.TCPFlow)
        assert tcp_message

        state = self.connections[flow]

        for message in flow.messages[state.message_count :]:
            if message.from_client:
                buf = state.client_buf
            else:
                buf = state.server_buf
            buf += message.content

            if state.message_count == 0 and flow.metadata["quic_is_unidirectional"]:
                h3_buf = Buffer(data=bytes(buf[:8]))
                stream_type = h3_buf.pull_uint_var()
                consumed = h3_buf.tell()
                del buf[:consumed]
                state.frames[0] = [StreamType(stream_type)]

            while True:
                h3_buf = Buffer(data=bytes(buf[:16]))
                try:
                    frame_type = h3_buf.pull_uint_var()
                    frame_size = h3_buf.pull_uint_var()
                except BufferReadError:
                    break

                consumed = h3_buf.tell()

                if len(buf) < consumed + frame_size:
                    break

                frame_data = bytes(buf[consumed : consumed + frame_size])

                frame = Frame(frame_type, frame_data)

                state.frames.setdefault(state.message_count, []).append(frame)

                del buf[: consumed + frame_size]

            state.message_count += 1

        frames = state.frames.get(flow.messages.index(tcp_message), [])
        if not frames:
            return ""
        else:
            return "\n\n".join(frame.pretty() for frame in frames)

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        flow = metadata.flow
        return (
            2
            * float(bool(flow and is_h3_alpn(flow.client_conn.alpn)))
            * float(isinstance(flow, tcp.TCPFlow))
        )


http3 = Http3Contentview()
