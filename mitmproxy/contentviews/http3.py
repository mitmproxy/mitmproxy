from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field

from aioquic.h3.connection import Setting, parse_settings

from mitmproxy import flow, tcp
from . import base
from .hex import ViewHex
from ..proxy.layers.http import is_h3_alpn  # type: ignore

from aioquic.buffer import Buffer, BufferReadError
import pylsqpack


@dataclass(frozen=True)
class Frame:
    """Representation of an HTTP/3 frame."""
    type: int
    data: bytes

    def pretty(self):
        frame_name = f"0x{self.type:x} Frame"
        if self.type == 0:
            frame_name = "DATA Frame"
        elif self.type == 1:
            try:
                hdrs = pylsqpack.Decoder(4096, 16).feed_header(0, self.data)[1]
                return [
                    [("header", "HEADERS Frame")],
                    *base.format_pairs(hdrs)
                ]
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
                    settings.append((key, f"0x{v:x}"))
                return [
                    [("header", "SETTINGS Frame")],
                    *base.format_pairs(settings)
                ]
        return [
            [("header", frame_name)],
            *ViewHex._format(self.data),
        ]


@dataclass
class ConnectionState:
    message_count: int = 0
    frames: dict[int, list[Frame]] = field(default_factory=dict)
    client_buf: bytearray = field(default_factory=bytearray)
    server_buf: bytearray = field(default_factory=bytearray)


class ViewHttp3(base.View):
    name = "HTTP/3 Frames"

    def __init__(self):
        self.connections: defaultdict[tcp.TCPFlow, ConnectionState] = defaultdict(ConnectionState)

    def __call__(
        self,
        data,
        flow: flow.Flow | None = None,
        tcp_message: tcp.TCPMessage | None = None,
        **metadata
    ):
        assert isinstance(flow, tcp.TCPFlow)
        assert tcp_message

        state = self.connections[flow]

        for message in flow.messages[state.message_count:]:
            if message.from_client:
                buf = state.client_buf
            else:
                buf = state.server_buf
            buf += message.content

            # TODO: It would be much better to know if the stream is unidirectional.
            if buf.startswith(b"\x00\x04"):
                del buf[:1]

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

                frame_data = bytes(buf[consumed:consumed + frame_size])

                frame = Frame(frame_type, frame_data)

                state.frames.setdefault(state.message_count, []).append(frame)

                del buf[:consumed + frame_size]

            state.message_count += 1

        frames = state.frames.get(flow.messages.index(tcp_message), [])
        if not frames:
            return "HTTP/3", []  # base.format_text(f"(no complete frames here, {state=})")
        else:
            return "HTTP/3", fmt_frames(frames)

    def render_priority(
        self,
        data: bytes,
        flow: flow.Flow | None = None,
        **metadata
    ) -> float:
        return 2 * float(bool(flow and is_h3_alpn(flow.client_conn.alpn))) * float(isinstance(flow, tcp.TCPFlow))


def fmt_frames(frames: list[Frame]) -> Iterator[base.TViewLine]:
    for i, frame in enumerate(frames):
        if i > 0:
            yield [("text", "")]
        yield from frame.pretty()
