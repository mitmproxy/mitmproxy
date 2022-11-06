import collections.abc
from typing import Callable, Iterable, Optional
import pytest
import pylsqpack

from aioquic._buffer import Buffer
from aioquic.h3.connection import FrameType, StreamType, Headers, Setting, encode_frame, encode_uint_var, encode_settings, parse_settings

from mitmproxy import connection
from mitmproxy.http import HTTPFlow
from mitmproxy.proxy import commands, context, layers
from mitmproxy.proxy.layers import http, quic
from test.mitmproxy.proxy import tutils


example_request_headers = [
    (b":method", b"GET"),
    (b":scheme", b"http"),
    (b":path", b"/"),
    (b":authority", b"example.com"),
]


class CallbackPlaceholder(tutils._Placeholder[bytes]):
    """Data placeholder that invokes a callback once its bytes get set."""
    def __init__(self, cb: Callable[[bytes], None]):
        super().__init__(bytes)
        self._cb = cb

    def setdefault(self, value: bytes) -> None:
        if self._obj is None:
            self._cb(value)
        return super().setdefault(value)


class DelayedPlaceholder(tutils._Placeholder[bytes]):
    """Data placeholder that resolves its bytes when needed."""
    def __init__(self, resolve: Callable[[], bytes]):
        super().__init__(bytes)
        self._resolve = resolve

    def __call__(self) -> bytes:
        if self._obj is None:
            self._obj = self._resolve()
        return super().__call__()


class MultiPlaybook(tutils.Playbook):
    """Playbook that allows multiple events and commands to be registered at once."""
    def __lshift__(self, c):
        if isinstance(c, collections.abc.Iterable):
            for c_i in c:
                super().__lshift__(c_i)
        else:
            super().__lshift__(c)
        return self

    def __rshift__(self, e):
        if isinstance(e, collections.abc.Iterable):
            for e_i in e:
                super().__rshift__(e_i)
        else:
            super().__rshift__(e)
        return self


class FrameFactory:
    """Helper class for generating QUIC stream events and commands."""
    def __init__(
        self,
        conn: connection.Connection,
        is_client: bool
    ) -> None:
        self.conn = conn
        self.is_client = is_client
        self.decoder = pylsqpack.Decoder(
            max_table_capacity=4096,
            blocked_streams=16,
        )
        self.decoder_placeholder: Optional[tutils.Placeholder(bytes)] = None
        self.encoder = pylsqpack.Encoder()
        self.encoder_placeholder: Optional[tutils.Placeholder(bytes)] = None
        self.peer_stream_id: dict[StreamType, int] = {}
        self.local_stream_id: dict[StreamType, int] = {}
        self.max_push_id: Optional[int] = None

    def get_default_stream_id(
        self,
        stream_type: StreamType,
        for_local: bool
    ) -> int:
        if stream_type == StreamType.CONTROL:
            stream_id = 2
        elif stream_type == StreamType.QPACK_ENCODER:
            stream_id = 6
        elif stream_type == StreamType.QPACK_DECODER:
            stream_id = 10
        else:
            raise AssertionError(stream_type)
        if self.is_client is not for_local:
            stream_id = stream_id + 1
        return stream_id

    def send_stream_type(
        self,
        stream_type: StreamType,
        stream_id: Optional[int] = None,
    ) -> quic.SendQuicStreamData:
        assert stream_type not in self.peer_stream_id
        if stream_id is None:
            stream_id = self.get_default_stream_id(
                stream_type, for_local=False
            )
        self.peer_stream_id[stream_type] = stream_id
        return quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=stream_id,
            data=encode_uint_var(stream_type),
            end_stream=False,
        )

    def receive_stream_type(
        self,
        stream_type: StreamType,
        stream_id: Optional[int] = None,
    ) -> quic.QuicStreamDataReceived:
        assert stream_type not in self.local_stream_id
        if stream_id is None:
            stream_id = self.get_default_stream_id(
                stream_type, for_local=True
            )
        self.local_stream_id[stream_type] = stream_id
        return quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=stream_id,
            data=encode_uint_var(stream_type),
            end_stream=False,
        )

    def send_settings(self) -> quic.SendQuicStreamData:
        assert self.encoder_placeholder is None
        placeholder = tutils.Placeholder(bytes)
        self.encoder_placeholder = placeholder

        def cb(data: bytes) -> None:
            buf = Buffer(data=data)
            assert buf.pull_uint_var() == FrameType.SETTINGS
            settings = parse_settings(buf.pull_bytes(buf.pull_uint_var()))
            placeholder.setdefault(self.encoder.apply_settings(
                max_table_capacity=settings[Setting.QPACK_MAX_TABLE_CAPACITY],
                blocked_streams=settings[Setting.QPACK_BLOCKED_STREAMS],
            ))

        return quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=self.peer_stream_id[StreamType.CONTROL],
            data=CallbackPlaceholder(cb),
            end_stream=False,
        )

    def send_max_push_id(self) -> quic.SendQuicStreamData:
        def cb(data: bytes) -> None:
            buf = Buffer(data=data)
            assert buf.pull_uint_var() == FrameType.MAX_PUSH_ID
            buf = Buffer(data=buf.pull_bytes(buf.pull_uint_var()))
            self.max_push_id = buf.pull_uint_var()
            assert buf.eof()

        return quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=self.peer_stream_id[StreamType.CONTROL],
            data=CallbackPlaceholder(cb),
            end_stream=False,
        )

    def receive_settings(
        self,
        settings: dict[int, int] = {
            Setting.QPACK_MAX_TABLE_CAPACITY: 4096,
            Setting.QPACK_BLOCKED_STREAMS: 16,
            Setting.ENABLE_CONNECT_PROTOCOL: 1,
            Setting.DUMMY: 1,
        },
    ) -> quic.QuicStreamDataReceived:
        return quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=self.local_stream_id[StreamType.CONTROL],
            data=encode_frame(FrameType.SETTINGS, encode_settings(settings)),
            end_stream=False,
        )

    def send_encoder(self) -> quic.SendQuicStreamData:
        def cb(data: bytes) -> bytes:
            self.decoder.feed_encoder(data)
            return data

        return quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=self.peer_stream_id[StreamType.QPACK_ENCODER],
            data=CallbackPlaceholder(cb),
            end_stream=False,
        )

    def receive_encoder(self) -> quic.QuicStreamDataReceived:
        assert self.encoder_placeholder is not None
        placeholder = self.encoder_placeholder
        self.encoder_placeholder = None

        return quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=self.local_stream_id[StreamType.QPACK_ENCODER],
            data=placeholder,
            end_stream=False,
        )

    def send_data(
        self,
        data: bytes,
        stream_id: int = 0,
        end_stream: bool = False,
    ) -> quic.SendQuicStreamData:
        return quic.SendQuicStreamData(
            self.conn,
            stream_id=stream_id,
            data=encode_frame(FrameType.DATA, data),
            end_stream=end_stream,
        )

    def send_decoder(self) -> quic.SendQuicStreamData:
        def cb(data: bytes) -> None:
            self.encoder.feed_decoder(data)

        return quic.SendQuicStreamData(
            self.conn,
            stream_id=self.peer_stream_id[StreamType.QPACK_DECODER],
            data=CallbackPlaceholder(cb),
            end_stream=False,
        )

    def receive_decoder(self) -> quic.QuicStreamDataReceived:
        assert self.decoder_placeholder is not None
        placeholder = self.decoder_placeholder
        self.decoder_placeholder = None

        return quic.QuicStreamDataReceived(
            self.conn,
            stream_id=self.local_stream_id[StreamType.QPACK_DECODER],
            data=placeholder,
            end_stream=False,
        )

    def receive_headers(
        self,
        headers: Headers,
        stream_id: int = 0,
        end_stream: bool = False,
    ) -> Iterable[quic.QuicStreamDataReceived]:
        data = tutils.Placeholder(bytes)

        def encode() -> bytes:
            encoder, frame_data = self.encoder.encode(stream_id, headers)
            data.setdefault(encode_frame(FrameType.HEADERS, frame_data))
            return encoder

        yield quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=self.local_stream_id[StreamType.QPACK_ENCODER],
            data=DelayedPlaceholder(encode),
            end_stream=False,
        )
        yield quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=stream_id,
            data=data,
            end_stream=end_stream,
        )

    def send_headers(
        self,
        headers: Headers,
        stream_id: int = 0,
        end_stream: bool = False,
    ) -> Iterable[quic.SendQuicStreamData]:
        assert self.decoder_placeholder is None
        placeholder = tutils.Placeholder(bytes)
        self.decoder_placeholder = placeholder

        def decode(data: bytes) -> None:
            buf = Buffer(data=data)
            assert buf.pull_uint_var() == FrameType.HEADERS
            frame_data = buf.pull_bytes(buf.pull_uint_var())
            decoder, headers = self.decoder.feed_header(stream_id, frame_data)
            placeholder.setdefault(decoder)
            assert headers == headers

        yield self.send_encoder()
        yield quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=stream_id,
            data=CallbackPlaceholder(decode),
            end_stream=end_stream,
        )

    def receive_data(
        self,
        data: bytes,
        stream_id: int = 0,
        end_stream: bool = False,
    ) -> quic.QuicStreamDataReceived:
        return quic.QuicStreamDataReceived(
            connection=self.conn,
            stream_id=stream_id,
            data=encode_frame(FrameType.DATA, data),
            end_stream=end_stream,
        )

    def send_server_init(self) -> Iterable[quic.SendQuicStreamData]:
        yield self.send_stream_type(StreamType.CONTROL)
        yield self.send_settings()
        yield self.send_max_push_id()
        yield self.send_stream_type(StreamType.QPACK_ENCODER)
        yield self.send_stream_type(StreamType.QPACK_DECODER)


@pytest.fixture
def open_h3_server_conn():
    # this is a bit fake here (port 80, with alpn, but no tls - c'mon),
    # but we don't want to pollute our tests with TLS handshakes.
    server = connection.Server(("example.com", 80), transport_protocol="udp")
    server.state = connection.ConnectionState.OPEN
    server.alpn = b"h3"
    return server


def start_h3_client(tctx: context.Context) -> tuple[tutils.Playbook, FrameFactory]:
    tctx.client.alpn = b"h3"
    tctx.client.transport_protocol = "udp"

    playbook = MultiPlaybook(layers.HttpLayer(tctx, layers.http.HTTPMode.regular))
    cff = FrameFactory(conn=tctx.client, is_client=True)
    assert (
        playbook
        << cff.send_stream_type(StreamType.CONTROL)
        << cff.send_settings()
        << cff.send_stream_type(StreamType.QPACK_ENCODER)
        << cff.send_stream_type(StreamType.QPACK_DECODER)
        >> cff.receive_stream_type(StreamType.CONTROL)
        >> cff.receive_settings()
        << cff.send_encoder()
        >> cff.receive_stream_type(StreamType.QPACK_ENCODER)
        >> cff.receive_stream_type(StreamType.QPACK_DECODER)
        >> cff.receive_encoder()
    )
    return playbook, cff


def make_h3(open_connection: commands.OpenConnection) -> None:
    open_connection.connection.alpn = b"h3"
    open_connection.connection.transport_protocol = "udp"


def test_simple(tctx: context.Context):
    playbook, cff = start_h3_client(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    assert (
        playbook
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << http.HttpRequestHeadersHook(flow)
        << cff.send_decoder()
        >> tutils.reply(to=http.HttpRequestHeadersHook(flow))
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        << commands.OpenConnection(server)
        >> tutils.reply(None, side_effect=make_h3)
        << sff.send_server_init()
        << sff.send_headers(example_request_headers, end_stream=True)
    )
