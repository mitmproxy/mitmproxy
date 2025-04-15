from collections.abc import Callable
from collections.abc import Iterable

import pylsqpack
import pytest
from aioquic._buffer import Buffer
from aioquic.h3.connection import encode_frame
from aioquic.h3.connection import encode_settings
from aioquic.h3.connection import encode_uint_var
from aioquic.h3.connection import ErrorCode
from aioquic.h3.connection import FrameType
from aioquic.h3.connection import Headers as H3Headers
from aioquic.h3.connection import parse_settings
from aioquic.h3.connection import Setting
from aioquic.h3.connection import StreamType
from aioquic.quic.packet import QuicErrorCode

from mitmproxy import connection
from mitmproxy import version
from mitmproxy.flow import Error
from mitmproxy.http import Headers
from mitmproxy.http import HTTPFlow
from mitmproxy.http import Request
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layers
from mitmproxy.proxy.layers import http
from mitmproxy.proxy.layers import quic
from mitmproxy.proxy.layers.http._http3 import Http3Client
from test.mitmproxy.proxy import tutils

example_request_headers = [
    (b":method", b"GET"),
    (b":scheme", b"http"),
    (b":path", b"/"),
    (b":authority", b"example.com"),
]

example_response_headers = [(b":status", b"200")]

example_request_trailers = [(b"req-trailer-a", b"a"), (b"req-trailer-b", b"b")]

example_response_trailers = [(b"resp-trailer-a", b"a"), (b"resp-trailer-b", b"b")]


def decode_frame(frame_type: int, frame_data: bytes) -> bytes:
    buf = Buffer(data=frame_data)
    assert buf.pull_uint_var() == frame_type
    return buf.pull_bytes(buf.pull_uint_var())


class CallbackPlaceholder(tutils._Placeholder[bytes]):
    """Data placeholder that invokes a callback once its bytes get set."""

    def __init__(self, cb: Callable[[bytes], None]):
        super().__init__(bytes)
        self._cb = cb

    def setdefault(self, value: bytes) -> bytes:
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


class FrameFactory:
    """Helper class for generating QUIC stream events and commands."""

    def __init__(self, conn: connection.Connection, is_client: bool) -> None:
        self.conn = conn
        self.is_client = is_client
        self.decoder = pylsqpack.Decoder(
            max_table_capacity=4096,
            blocked_streams=16,
        )
        self.decoder_placeholders: list[tutils.Placeholder[bytes]] = []
        self.encoder = pylsqpack.Encoder()
        self.encoder_placeholder: tutils.Placeholder[bytes] | None = None
        self.peer_stream_id: dict[StreamType, int] = {}
        self.local_stream_id: dict[StreamType, int] = {}

    def get_default_stream_id(self, stream_type: StreamType, for_local: bool) -> int:
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
        stream_id: int | None = None,
    ) -> quic.SendQuicStreamData:
        assert stream_type not in self.peer_stream_id
        if stream_id is None:
            stream_id = self.get_default_stream_id(stream_type, for_local=False)
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
        stream_id: int | None = None,
    ) -> quic.QuicStreamDataReceived:
        assert stream_type not in self.local_stream_id
        if stream_id is None:
            stream_id = self.get_default_stream_id(stream_type, for_local=True)
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
            placeholder.setdefault(
                self.encoder.apply_settings(
                    max_table_capacity=settings[Setting.QPACK_MAX_TABLE_CAPACITY],
                    blocked_streams=settings[Setting.QPACK_BLOCKED_STREAMS],
                )
            )

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
        assert self.decoder_placeholders
        placeholder = self.decoder_placeholders.pop(0)

        return quic.QuicStreamDataReceived(
            self.conn,
            stream_id=self.local_stream_id[StreamType.QPACK_DECODER],
            data=placeholder,
            end_stream=False,
        )

    def send_headers(
        self,
        headers: H3Headers,
        stream_id: int = 0,
        end_stream: bool = False,
    ) -> Iterable[quic.SendQuicStreamData]:
        placeholder = tutils.Placeholder(bytes)
        self.decoder_placeholders.append(placeholder)

        def decode(data: bytes) -> None:
            buf = Buffer(data=data)
            assert buf.pull_uint_var() == FrameType.HEADERS
            frame_data = buf.pull_bytes(buf.pull_uint_var())
            decoder, actual_headers = self.decoder.feed_header(stream_id, frame_data)
            placeholder.setdefault(decoder)
            assert headers == actual_headers

        yield self.send_encoder()
        yield quic.SendQuicStreamData(
            connection=self.conn,
            stream_id=stream_id,
            data=CallbackPlaceholder(decode),
            end_stream=end_stream,
        )

    def receive_headers(
        self,
        headers: H3Headers,
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

    def send_reset(
        self, error_code: ErrorCode, stream_id: int = 0
    ) -> quic.ResetQuicStream:
        return quic.ResetQuicStream(
            connection=self.conn,
            stream_id=stream_id,
            error_code=int(error_code),
        )

    def receive_reset(
        self, error_code: ErrorCode, stream_id: int = 0
    ) -> quic.QuicStreamReset:
        return quic.QuicStreamReset(
            connection=self.conn,
            stream_id=stream_id,
            error_code=int(error_code),
        )

    def send_stop(
        self, error_code: ErrorCode, stream_id: int = 0
    ) -> quic.StopSendingQuicStream:
        return quic.StopSendingQuicStream(
            connection=self.conn,
            stream_id=stream_id,
            error_code=int(error_code),
        )

    def receive_stop(
        self, error_code: ErrorCode, stream_id: int = 0
    ) -> quic.QuicStreamStopSending:
        return quic.QuicStreamStopSending(
            connection=self.conn,
            stream_id=stream_id,
            error_code=int(error_code),
        )

    def send_init(self) -> Iterable[quic.SendQuicStreamData]:
        yield self.send_stream_type(StreamType.CONTROL)
        yield self.send_settings()
        yield self.send_stream_type(StreamType.QPACK_ENCODER)
        yield self.send_stream_type(StreamType.QPACK_DECODER)

    def receive_init(self) -> Iterable[quic.QuicStreamDataReceived]:
        yield self.receive_stream_type(StreamType.CONTROL)
        yield self.receive_stream_type(StreamType.QPACK_ENCODER)
        yield self.receive_stream_type(StreamType.QPACK_DECODER)
        yield self.receive_settings()

    @property
    def is_done(self) -> bool:
        return self.encoder_placeholder is None and not self.decoder_placeholders


@pytest.fixture
def open_h3_server_conn():
    # this is a bit fake here (port 80, with alpn, but no tls - c'mon),
    # but we don't want to pollute our tests with TLS handshakes.
    server = connection.Server(address=("example.com", 80), transport_protocol="udp")
    server.state = connection.ConnectionState.OPEN
    server.alpn = b"h3"
    return server


def start_h3_proxy(tctx: context.Context) -> tuple[tutils.Playbook, FrameFactory]:
    tctx.client.alpn = b"h3"
    tctx.client.transport_protocol = "udp"
    tctx.server.transport_protocol = "udp"

    playbook = tutils.Playbook(layers.HttpLayer(tctx, layers.http.HTTPMode.regular))
    cff = FrameFactory(conn=tctx.client, is_client=True)
    assert (
        playbook
        << cff.send_init()
        >> cff.receive_init()
        << cff.send_encoder()
        >> cff.receive_encoder()
    )
    return playbook, cff


def make_h3(open_connection: commands.OpenConnection) -> None:
    open_connection.connection.alpn = b"h3"


def test_ignore_push(tctx: context.Context):
    playbook, cff = start_h3_proxy(tctx)


def test_fail_without_header(tctx: context.Context):
    playbook = tutils.Playbook(layers.http.Http3Server(tctx))
    cff = FrameFactory(tctx.client, is_client=True)
    assert (
        playbook
        << cff.send_init()
        >> cff.receive_init()
        << cff.send_encoder()
        >> cff.receive_encoder()
        >> http.ResponseProtocolError(0, "first message", http.ErrorCode.KILL)
        << cff.send_reset(ErrorCode.H3_INTERNAL_ERROR)
        << cff.send_stop(ErrorCode.H3_INTERNAL_ERROR)
    )
    assert cff.is_done


def test_invalid_header(tctx: context.Context):
    playbook, cff = start_h3_proxy(tctx)
    assert (
        playbook
        >> cff.receive_headers(
            [
                (b":method", b"CONNECT"),
                (b":path", b"/"),
                (b":authority", b"example.com"),
            ],
            end_stream=True,
        )
        << cff.send_decoder()  # for receive_headers
        << quic.CloseQuicConnection(
            tctx.client,
            error_code=ErrorCode.H3_GENERAL_PROTOCOL_ERROR.value,
            frame_type=None,
            reason_phrase="Invalid HTTP/3 request headers: Required pseudo header is missing: b':scheme'",
        )
        # ensure that once we close, we don't process messages anymore
        >> cff.receive_headers(
            [
                (b":method", b"CONNECT"),
                (b":path", b"/"),
                (b":authority", b"example.com"),
            ],
            end_stream=True,
        )
    )


def test_simple(tctx: context.Context):
    playbook, cff = start_h3_proxy(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    assert (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply(None, side_effect=make_h3)
        << sff.send_init()
        << sff.send_headers(example_request_headers, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
        # response server
        >> sff.receive_headers(example_response_headers)
        << (response := http.HttpResponseHeadersHook(flow))
        << sff.send_decoder()  # for receive_headers
        >> tutils.reply(to=response)
        >> sff.receive_data(b"Hello, World!", end_stream=True)
        << http.HttpResponseHook(flow)
        >> tutils.reply()
        # response client
        << cff.send_headers(example_response_headers)
        << cff.send_data(b"Hello, World!")
        << cff.send_data(b"", end_stream=True)
        >> cff.receive_decoder()  # for send_headers
    )
    assert cff.is_done and sff.is_done
    assert flow().request.url == "http://example.com/"
    assert flow().response.text == "Hello, World!"


@pytest.mark.parametrize("stream", ["stream", ""])
def test_response_trailers(
    tctx: context.Context,
    open_h3_server_conn: connection.Server,
    stream: str,
):
    playbook, cff = start_h3_proxy(tctx)
    tctx.server = open_h3_server_conn
    sff = FrameFactory(tctx.server, is_client=False)

    def enable_streaming(flow: HTTPFlow):
        flow.response.stream = stream

    flow = tutils.Placeholder(HTTPFlow)
    (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << sff.send_init()
        << sff.send_headers(example_request_headers, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
        # response server
        >> sff.receive_headers(example_response_headers)
        << (response_headers := http.HttpResponseHeadersHook(flow))
        << sff.send_decoder()  # for receive_headers
        >> tutils.reply(to=response_headers, side_effect=enable_streaming)
    )
    if stream:
        (
            playbook
            << cff.send_headers(example_response_headers)
            >> cff.receive_decoder()  # for send_headers
            >> sff.receive_data(b"Hello, World!")
            << cff.send_data(b"Hello, World!")
        )
    else:
        playbook >> sff.receive_data(b"Hello, World!")
    assert (
        playbook
        >> sff.receive_headers(example_response_trailers, end_stream=True)
        << (response := http.HttpResponseHook(flow))
        << sff.send_decoder()  # for receive_headers
    )
    assert flow().response.trailers
    del flow().response.trailers["resp-trailer-a"]
    if stream:
        assert (
            playbook
            >> tutils.reply(to=response)
            << cff.send_headers(example_response_trailers[1:], end_stream=True)
            >> cff.receive_decoder()  # for send_headers
        )
    else:
        assert (
            playbook
            >> tutils.reply(to=response)
            << cff.send_headers(example_response_headers)
            << cff.send_data(b"Hello, World!")
            << cff.send_headers(example_response_trailers[1:], end_stream=True)
            >> cff.receive_decoder()  # for send_headers
            >> cff.receive_decoder()  # for send_headers
        )
    assert cff.is_done and sff.is_done


@pytest.mark.parametrize("stream", ["stream", ""])
def test_request_trailers(
    tctx: context.Context,
    open_h3_server_conn: connection.Server,
    stream: str,
):
    playbook, cff = start_h3_proxy(tctx)
    tctx.server = open_h3_server_conn
    sff = FrameFactory(tctx.server, is_client=False)

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = stream

    flow = tutils.Placeholder(HTTPFlow)
    (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers)
        << (request_headers := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> cff.receive_data(b"Hello World!")
        >> tutils.reply(to=request_headers, side_effect=enable_streaming)
    )
    if not stream:
        (
            playbook
            >> cff.receive_headers(example_request_trailers, end_stream=True)
            << (request := http.HttpRequestHook(flow))
            << cff.send_decoder()  # for receive_headers
            >> tutils.reply(to=request)
        )
    (
        playbook
        # request server
        << sff.send_init()
        << sff.send_headers(example_request_headers)
        << sff.send_data(b"Hello World!")
    )
    if not stream:
        playbook << sff.send_headers(example_request_trailers, end_stream=True)
    (
        playbook
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
    )
    if stream:
        (
            playbook
            >> cff.receive_headers(example_request_trailers, end_stream=True)
            << (request := http.HttpRequestHook(flow))
            << cff.send_decoder()  # for receive_headers
            >> tutils.reply(to=request)
            << sff.send_headers(example_request_trailers, end_stream=True)
        )
    assert playbook >> sff.receive_decoder()  # for send_headers

    assert cff.is_done and sff.is_done


def test_upstream_error(tctx: context.Context):
    playbook, cff = start_h3_proxy(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    err = tutils.Placeholder(bytes)
    assert (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply("oops server <> error")
        << http.HttpErrorHook(flow)
        >> tutils.reply()
        << cff.send_headers(
            [
                (b":status", b"502"),
                (b"server", version.MITMPROXY.encode()),
                (b"content-type", b"text/html"),
            ]
        )
        << quic.SendQuicStreamData(
            tctx.client,
            stream_id=0,
            data=err,
            end_stream=True,
        )
        >> cff.receive_decoder()  # for send_headers
    )
    assert cff.is_done
    data = decode_frame(FrameType.DATA, err())
    assert b"502 Bad Gateway" in data
    assert b"server &lt;&gt; error" in data


@pytest.mark.parametrize("stream", ["stream", ""])
@pytest.mark.parametrize("when", ["request", "response"])
@pytest.mark.parametrize("how", ["RST", "disconnect", "RST+disconnect"])
def test_http3_client_aborts(tctx: context.Context, stream: str, when: str, how: str):
    """
    Test handling of the case where a client aborts during request or response transmission.

    If the client aborts the request transmission, we must trigger an error hook,
    if the client disconnects during response transmission, no error hook is triggered.
    """
    server = tutils.Placeholder(connection.Server)
    flow = tutils.Placeholder(HTTPFlow)
    playbook, cff = start_h3_proxy(tctx)

    def enable_request_streaming(flow: HTTPFlow):
        flow.request.stream = True

    def enable_response_streaming(flow: HTTPFlow):
        flow.response.stream = True

    assert (
        playbook
        >> cff.receive_headers(example_request_headers)
        << (request_headers := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
    )
    if stream and when == "request":
        assert (
            playbook
            >> tutils.reply(side_effect=enable_request_streaming, to=request_headers)
            << commands.OpenConnection(server)
            >> tutils.reply(None)
            << commands.SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        )
    else:
        assert playbook >> tutils.reply(to=request_headers)

    if when == "request":
        if "RST" in how:
            playbook >> cff.receive_reset(ErrorCode.H3_REQUEST_CANCELLED)
        else:
            playbook >> quic.QuicConnectionClosed(
                tctx.client,
                error_code=ErrorCode.H3_REQUEST_CANCELLED.value,
                frame_type=None,
                reason_phrase="peer closed connection",
            )

        if stream:
            playbook << commands.CloseConnection(server)
        playbook << (error_hook := http.HttpErrorHook(flow))
        if "RST" in how:
            playbook << cff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
        playbook >> tutils.reply(to=error_hook)

        if how == "RST+disconnect":
            playbook >> quic.QuicConnectionClosed(
                tctx.client,
                error_code=ErrorCode.H3_NO_ERROR.value,
                frame_type=None,
                reason_phrase="peer closed connection",
            )
        assert playbook
        assert (
            "stream closed by client" in flow().error.msg
            or "peer closed connection" in flow().error.msg
        )
        return

    assert (
        playbook
        >> cff.receive_data(b"", end_stream=True)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        << commands.OpenConnection(server)
        >> tutils.reply(None)
        << commands.SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> events.DataReceived(
            server, b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\n123"
        )
        << http.HttpResponseHeadersHook(flow)
    )
    if stream:
        assert (
            playbook
            >> tutils.reply(side_effect=enable_response_streaming)
            << cff.send_headers(
                [
                    (b":status", b"200"),
                    (b"content-length", b"6"),
                ]
            )
            << cff.send_data(b"123")
        )
    else:
        assert playbook >> tutils.reply()

    if "RST" in how:
        playbook >> cff.receive_reset(ErrorCode.H3_REQUEST_CANCELLED)
    else:
        playbook >> quic.QuicConnectionClosed(
            tctx.client,
            error_code=ErrorCode.H3_REQUEST_CANCELLED.value,
            frame_type=None,
            reason_phrase="peer closed connection",
        )

    playbook << commands.CloseConnection(server)
    playbook << (error_hook := http.HttpErrorHook(flow))
    if "RST" in how:
        playbook << cff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
    playbook >> tutils.reply(to=error_hook)
    assert playbook

    if how == "RST+disconnect":
        playbook >> quic.QuicConnectionClosed(
            tctx.client,
            error_code=ErrorCode.H3_REQUEST_CANCELLED.value,
            frame_type=None,
            reason_phrase="peer closed connection",
        )
        assert playbook

    if "RST" in how:
        assert "stream closed by client" in flow().error.msg
    else:
        assert "peer closed connection" in flow().error.msg


def test_rst_then_close(tctx):
    """
    Test that we properly handle the case of a client that first causes protocol errors and then disconnects.

    This is slightly different to H2, as QUIC will close the connection immediately.
    """
    playbook, cff = start_h3_proxy(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    err = tutils.Placeholder(str)

    assert (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << (open := commands.OpenConnection(server))
        >> cff.receive_data(b"unexpected data frame")
        << quic.CloseQuicConnection(
            tctx.client,
            error_code=QuicErrorCode.PROTOCOL_VIOLATION.value,
            frame_type=None,
            reason_phrase=err,
        )
        >> quic.QuicConnectionClosed(
            tctx.client,
            error_code=QuicErrorCode.PROTOCOL_VIOLATION.value,
            frame_type=None,
            reason_phrase=err,
        )
        >> tutils.reply("connection cancelled", to=open)
        << http.HttpErrorHook(flow)
        >> tutils.reply()
    )
    assert flow().error.msg == "connection cancelled"


def test_cancel_then_server_disconnect(tctx: context.Context):
    """
    Test that we properly handle the case of the following event sequence:
        - client cancels a stream
        - we start an error hook
        - server disconnects
        - error hook completes.
    """
    playbook, cff = start_h3_proxy(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    assert (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply(None)
        << commands.SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        # cancel
        >> cff.receive_reset(error_code=ErrorCode.H3_REQUEST_CANCELLED)
        << commands.CloseConnection(server)
        << (err_hook := http.HttpErrorHook(flow))
        << cff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
        >> tutils.reply(to=err_hook)
        >> events.ConnectionClosed(server)
        << None
    )
    assert cff.is_done


def test_cancel_during_response_hook(tctx: context.Context):
    """
    Test that we properly handle the case of the following event sequence:
        - we receive a server response
        - we trigger the response hook
        - the client cancels the stream
        - the response hook completes

    Given that we have already triggered the response hook, we don't want to trigger the error hook.
    """
    playbook, cff = start_h3_proxy(tctx)
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    assert (
        playbook
        # request client
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request)
        << http.HttpRequestHook(flow)
        >> tutils.reply()
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply(None)
        << commands.SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        # response server
        >> events.DataReceived(server, b"HTTP/1.1 204 No Content\r\n\r\n")
        << (reponse_headers := http.HttpResponseHeadersHook(flow))
        << commands.CloseConnection(server)
        >> tutils.reply(to=reponse_headers)
        << (response := http.HttpResponseHook(flow))
        >> cff.receive_reset(error_code=ErrorCode.H3_REQUEST_CANCELLED)
        << cff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
        >> tutils.reply(to=response)
    )
    assert cff.is_done


def test_stream_concurrency(tctx: context.Context):
    """Test that we can send an intercepted request with a lower stream id than one that has already been sent."""
    playbook, cff = start_h3_proxy(tctx)
    flow1 = tutils.Placeholder(HTTPFlow)
    flow2 = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    headers1 = [*example_request_headers, (b"x-order", b"1")]
    headers2 = [*example_request_headers, (b"x-order", b"2")]
    assert (
        playbook
        # request client
        >> cff.receive_headers(headers1, stream_id=0, end_stream=True)
        << (request_header1 := http.HttpRequestHeadersHook(flow1))
        << cff.send_decoder()  # for receive_headers
        >> cff.receive_headers(headers2, stream_id=4, end_stream=True)
        << (request_header2 := http.HttpRequestHeadersHook(flow2))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request_header1)
        << (request1 := http.HttpRequestHook(flow1))
        >> tutils.reply(to=request_header2)
        << (request2 := http.HttpRequestHook(flow2))
        # req 2 overtakes 1 and we already have a reply:
        >> tutils.reply(to=request2)
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply(None, side_effect=make_h3)
        << sff.send_init()
        << sff.send_headers(headers2, stream_id=0, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
        >> tutils.reply(to=request1)
        << sff.send_headers(headers1, stream_id=4, end_stream=True)
        >> sff.receive_decoder()  # for send_headers
    )
    assert cff.is_done and sff.is_done


def test_stream_concurrent_get_connection(tctx: context.Context):
    """Test that an immediate second request for the same domain does not trigger a second connection attempt."""
    playbook, cff = start_h3_proxy(tctx)
    playbook.hooks = False
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    assert (
        playbook
        >> cff.receive_headers(example_request_headers, stream_id=0, end_stream=True)
        << cff.send_decoder()  # for receive_headers
        << (o := commands.OpenConnection(server))
        >> cff.receive_headers(example_request_headers, stream_id=4, end_stream=True)
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(None, to=o, side_effect=make_h3)
        << sff.send_init()
        << sff.send_headers(example_request_headers, stream_id=0, end_stream=True)
        << sff.send_headers(example_request_headers, stream_id=4, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
        >> sff.receive_decoder()  # for send_headers
    )
    assert cff.is_done and sff.is_done


def test_kill_stream(tctx: context.Context):
    """Test that we can kill individual streams."""
    playbook, cff = start_h3_proxy(tctx)
    flow1 = tutils.Placeholder(HTTPFlow)
    flow2 = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    headers1 = [*example_request_headers, (b"x-order", b"1")]
    headers2 = [*example_request_headers, (b"x-order", b"2")]

    def kill(flow: HTTPFlow):
        # Can't use flow.kill() here because that currently still depends on a reply object.
        flow.error = Error(Error.KILLED_MESSAGE)

    assert (
        playbook
        # request client
        >> cff.receive_headers(headers1, stream_id=0, end_stream=True)
        << (request_header1 := http.HttpRequestHeadersHook(flow1))
        << cff.send_decoder()  # for receive_headers
        >> cff.receive_headers(headers2, stream_id=4, end_stream=True)
        << (request_header2 := http.HttpRequestHeadersHook(flow2))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request_header2, side_effect=kill)
        << http.HttpErrorHook(flow2)
        >> tutils.reply()
        << cff.send_reset(ErrorCode.H3_INTERNAL_ERROR, stream_id=4)
        << cff.send_stop(ErrorCode.H3_INTERNAL_ERROR, stream_id=4)
        >> tutils.reply(to=request_header1)
        << http.HttpRequestHook(flow1)
        >> tutils.reply()
        # request server
        << commands.OpenConnection(server)
        >> tutils.reply(None, side_effect=make_h3)
        << sff.send_init()
        << sff.send_headers(headers1, stream_id=0, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
        >> sff.receive_encoder()
        >> sff.receive_decoder()  # for send_headers
    )
    assert cff.is_done and sff.is_done


@pytest.mark.parametrize("close_type", ["RESET_STREAM", "STOP_SENDING"])
def test_receive_stop_sending(tctx: context.Context, close_type: str):
    playbook, cff = start_h3_proxy(tctx)
    playbook.hooks = False
    flow = tutils.Placeholder(HTTPFlow)
    server = tutils.Placeholder(connection.Server)
    sff = FrameFactory(server, is_client=False)
    assert (
        playbook
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << cff.send_decoder()
        << commands.OpenConnection(server)
        >> tutils.reply(None, side_effect=make_h3)
        << sff.send_init()
        << sff.send_headers(example_request_headers, end_stream=True)
        >> sff.receive_init()
        << sff.send_encoder()
    )

    close1 = cff.receive_reset(ErrorCode.H3_REQUEST_CANCELLED)
    close2 = cff.receive_stop(ErrorCode.H3_REQUEST_CANCELLED)
    if close_type == "STOP_SENDING":
        close1, close2 = close2, close1

    assert (
        playbook
        # Client now closes the stream.
        >> close1
        # We shut down the server...
        << sff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
        << sff.send_stop(ErrorCode.H3_REQUEST_CANCELLED)
        << (err_hook := http.HttpErrorHook(flow))
        # ...and the client stream.
        << cff.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
        << (
            cff.send_stop(ErrorCode.H3_REQUEST_CANCELLED)
            if close_type == "STOP_SENDING"
            else None
        )
        >> tutils.reply(to=err_hook)
        # These don't do anything anymore.
        >> close2
        << None
        >> sff.receive_reset(ErrorCode.H3_REQUEST_CANCELLED)
        << None
        >> sff.receive_stop(ErrorCode.H3_REQUEST_CANCELLED)
        << None
    )
    assert flow().error.msg == "stream closed by client (H3_REQUEST_CANCELLED)"


class TestClient:
    def test_no_data_on_closed_stream(self, tctx: context.Context):
        frame_factory = FrameFactory(tctx.server, is_client=False)
        playbook = tutils.Playbook(Http3Client(tctx))
        req = Request.make("GET", "http://example.com/")
        resp = [(b":status", b"200")]
        assert (
            playbook
            << frame_factory.send_init()
            >> frame_factory.receive_init()
            << frame_factory.send_encoder()
            >> frame_factory.receive_encoder()
            >> http.RequestHeaders(1, req, end_stream=True)
            << frame_factory.send_headers(
                [
                    (b":method", b"GET"),
                    (b":scheme", b"http"),
                    (b":path", b"/"),
                    (b"content-length", b"0"),
                ],
                end_stream=True,
            )
            >> frame_factory.receive_decoder()  # for send_headers
            >> http.RequestEndOfMessage(1)
            >> frame_factory.receive_headers(resp)
            << http.ReceiveHttp(tutils.Placeholder(http.ResponseHeaders))
            << frame_factory.send_decoder()  # for receive_headers
            >> http.RequestProtocolError(
                1, "cancelled", code=http.ErrorCode.CLIENT_DISCONNECTED
            )
            << frame_factory.send_reset(ErrorCode.H3_REQUEST_CANCELLED)
            << frame_factory.send_stop(ErrorCode.H3_REQUEST_CANCELLED)
            >> frame_factory.receive_data(b"foo")
            << None
        )  # important: no ResponseData event here!

        assert frame_factory.is_done

    def test_ignore_wrong_order(self, tctx: context.Context):
        frame_factory = FrameFactory(tctx.server, is_client=False)
        playbook = tutils.Playbook(Http3Client(tctx))
        req = Request.make("GET", "http://example.com/")
        assert (
            playbook
            << frame_factory.send_init()
            >> frame_factory.receive_init()
            << frame_factory.send_encoder()
            >> frame_factory.receive_encoder()
            >> http.RequestTrailers(1, Headers([(b"x-trailer", b"")]))
            << commands.Log(
                "Received RequestTrailers(stream_id=0, trailers=Headers[(b'x-trailer', b'')]) unexpectedly: "
                "trailing HEADERS frame is not allowed in this state"
            )
            >> http.RequestEndOfMessage(1)
            << commands.Log(
                "Received RequestEndOfMessage(stream_id=0) unexpectedly: "
                "DATA frame is not allowed in this state"
            )
            >> http.RequestData(1, b"123")
            << commands.Log(
                "Received RequestData(stream_id=0, data=b'123') unexpectedly: "
                "DATA frame is not allowed in this state"
            )
            >> http.RequestHeaders(1, req, end_stream=False)
            << frame_factory.send_headers(
                [
                    (b":method", b"GET"),
                    (b":scheme", b"http"),
                    (b":path", b"/"),
                    (b"content-length", b"0"),
                ],
                end_stream=False,
            )
            >> frame_factory.receive_decoder()  # for send_headers
            >> http.RequestHeaders(1, req, end_stream=False)
            << commands.Log(
                "Received RequestHeaders(stream_id=0, request=Request(GET example.com:80/),"
                " end_stream=False, replay_flow=None) unexpectedly: "
                "initial HEADERS frame is not allowed in this state"
            )
        )


def test_early_server_data(tctx: context.Context):
    playbook, cff = start_h3_proxy(tctx)
    sff = FrameFactory(tctx.server, is_client=False)

    tctx.server.address = ("example.com", 80)
    tctx.server.state = connection.ConnectionState.OPEN
    tctx.server.alpn = b"h3"

    flow = tutils.Placeholder(HTTPFlow)
    assert (
        playbook
        >> cff.receive_headers(example_request_headers, end_stream=True)
        << (request_header := http.HttpRequestHeadersHook(flow))
        << cff.send_decoder()  # for receive_headers
        >> tutils.reply(to=request_header)
        << (request := http.HttpRequestHook(flow))
        # Surprise! We get data from the server before the request hook finishes.
        >> sff.receive_stream_type(StreamType.CONTROL)
        << sff.send_init()
        >> sff.receive_stream_type(StreamType.QPACK_ENCODER)
        >> sff.receive_stream_type(StreamType.QPACK_DECODER)
        >> sff.receive_settings()
        << sff.send_encoder()
        >> sff.receive_encoder()
        # Request hook finishes...
        >> tutils.reply(to=request)
        << sff.send_headers(example_request_headers, end_stream=True)
    )
