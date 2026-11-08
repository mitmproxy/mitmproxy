import time
from logging import DEBUG

import h2.settings
import hpack
import hyperframe.frame
import pytest
from h2.errors import ErrorCodes

from mitmproxy.connection import ConnectionState
from mitmproxy.connection import Server
from mitmproxy.flow import Error
from mitmproxy.http import Headers
from mitmproxy.http import HTTPFlow
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.proxy.commands import CloseConnection
from mitmproxy.proxy.commands import Log
from mitmproxy.proxy.commands import OpenConnection
from mitmproxy.proxy.commands import RequestWakeup
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import ConnectionClosed
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers import http
from mitmproxy.proxy.layers.http import ErrorCode
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.http._http2 import Http2Client
from mitmproxy.proxy.layers.http._http2 import split_pseudo_headers
from test.mitmproxy.proxy.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy.tutils import Placeholder
from test.mitmproxy.proxy.tutils import Playbook
from test.mitmproxy.proxy.tutils import reply

example_request_headers = (
    (b":method", b"GET"),
    (b":scheme", b"http"),
    (b":path", b"/"),
    (b":authority", b"example.com"),
)

example_response_headers = ((b":status", b"200"),)

example_request_trailers = ((b"req-trailer-a", b"a"), (b"req-trailer-b", b"b"))

example_response_trailers = ((b"resp-trailer-a", b"a"), (b"resp-trailer-b", b"b"))


@pytest.fixture
def open_h2_server_conn():
    # this is a bit fake here (port 80, with alpn, but no tls - c'mon),
    # but we don't want to pollute our tests with TLS handshakes.
    s = Server(address=("example.com", 80))
    s.state = ConnectionState.OPEN
    s.alpn = b"h2"
    return s


def decode_frames(data: bytes) -> list[hyperframe.frame.Frame]:
    # swallow preamble
    if data.startswith(b"PRI * HTTP/2.0"):
        data = data[24:]
    frames = []
    while data:
        f, length = hyperframe.frame.Frame.parse_frame_header(data[:9])
        f.parse_body(memoryview(data[9 : 9 + length]))
        frames.append(f)
        data = data[9 + length :]
    return frames


def start_h2_client(tctx: Context, keepalive: int = 0) -> tuple[Playbook, FrameFactory]:
    tctx.client.alpn = b"h2"
    tctx.options.http2_ping_keepalive = keepalive
    frame_factory = FrameFactory()

    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))
    assert (
        playbook
        << SendData(tctx.client, Placeholder())  # initial settings frame
        >> DataReceived(tctx.client, frame_factory.preamble())
        >> DataReceived(
            tctx.client, frame_factory.build_settings_frame({}, ack=True).serialize()
        )
    )
    return playbook, frame_factory


def make_h2(open_connection: OpenConnection) -> None:
    assert isinstance(open_connection, OpenConnection), (
        f"Expected OpenConnection event, not {open_connection}"
    )
    open_connection.connection.alpn = b"h2"


def test_simple(tctx):
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
    )
    frames = decode_frames(initial())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]
    sff = FrameFactory()
    assert (
        playbook
        # a conforming h2 server would send settings first, we disregard this for now.
        >> DataReceived(
            server, sff.build_headers_frame(example_response_headers).serialize()
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        >> DataReceived(
            server,
            sff.build_data_frame(b"Hello, World!", flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize()
            + cff.build_data_frame(b"Hello, World!").serialize()
            + cff.build_data_frame(b"", flags=["END_STREAM"]).serialize(),
        )
    )
    assert flow().request.url == "http://example.com/"
    assert flow().response.text == "Hello, World!"


@pytest.mark.parametrize("stream", ["stream", ""])
def test_response_trailers(tctx: Context, open_h2_server_conn: Server, stream):
    playbook, cff = start_h2_client(tctx)
    tctx.server = open_h2_server_conn
    sff = FrameFactory()

    def enable_streaming(flow: HTTPFlow):
        flow.response.stream = bool(stream)

    flow = Placeholder(HTTPFlow)
    (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(tctx.server, Placeholder(bytes))
        # a conforming h2 server would send settings first, we disregard this for now.
        >> DataReceived(
            tctx.server,
            sff.build_headers_frame(example_response_headers).serialize()
            + sff.build_data_frame(b"Hello, World!").serialize(),
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
    )
    if stream:
        playbook << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize()
            + cff.build_data_frame(b"Hello, World!").serialize(),
        )
    assert (
        playbook
        >> DataReceived(
            tctx.server,
            sff.build_headers_frame(
                example_response_trailers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpResponseHook(flow)
    )
    assert flow().response.trailers
    del flow().response.trailers["resp-trailer-a"]
    if stream:
        assert (
            playbook
            >> reply()
            << SendData(
                tctx.client,
                cff.build_headers_frame(
                    example_response_trailers[1:], flags=["END_STREAM"]
                ).serialize(),
            )
        )
    else:
        assert (
            playbook
            >> reply()
            << SendData(
                tctx.client,
                cff.build_headers_frame(example_response_headers).serialize()
                + cff.build_data_frame(b"Hello, World!").serialize()
                + cff.build_headers_frame(
                    example_response_trailers[1:], flags=["END_STREAM"]
                ).serialize(),
            )
        )


@pytest.mark.parametrize("stream", ["stream", ""])
def test_request_trailers(tctx: Context, open_h2_server_conn: Server, stream):
    playbook, cff = start_h2_client(tctx)
    tctx.server = open_h2_server_conn

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = bool(stream)

    flow = Placeholder(HTTPFlow)
    server_data1 = Placeholder(bytes)
    server_data2 = Placeholder(bytes)
    (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(example_request_headers).serialize()
            + cff.build_data_frame(b"Hello, World!").serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
    )
    if stream:
        playbook << SendData(tctx.server, server_data1)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_trailers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(tctx.server, server_data2)
    )
    frames = decode_frames(server_data1.setdefault(b"") + server_data2())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
        hyperframe.frame.DataFrame,
        hyperframe.frame.HeadersFrame,
    ]


def test_upstream_error(tctx):
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    err = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply("oops server <> error")
        << http.HttpErrorHook(flow)
        >> reply()
        << SendData(tctx.client, err)
    )
    frames = decode_frames(err())
    assert [type(x) for x in frames] == [
        hyperframe.frame.HeadersFrame,
        hyperframe.frame.DataFrame,
    ]
    d = frames[1]
    assert isinstance(d, hyperframe.frame.DataFrame)
    assert b"502 Bad Gateway" in d.data
    assert b"server &lt;&gt; error" in d.data


@pytest.mark.parametrize("trailers", ["trailers", ""])
def test_long_response(tctx: Context, trailers):
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
    )
    frames = decode_frames(initial())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]
    sff = FrameFactory()
    assert (
        playbook
        # a conforming h2 server would send settings first, we disregard this for now.
        >> DataReceived(
            server, sff.build_headers_frame(example_response_headers).serialize()
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        >> DataReceived(
            server, sff.build_data_frame(b"a" * 10000, flags=[]).serialize()
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"a" * 10000, flags=[]).serialize(),
        )
    )
    if trailers:
        (
            playbook
            >> DataReceived(
                server,
                sff.build_headers_frame(
                    example_response_trailers, flags=["END_STREAM"]
                ).serialize(),
            )
        )
    else:
        (
            playbook
            >> DataReceived(
                server,
                sff.build_data_frame(b"", flags=["END_STREAM"]).serialize(),
            )
        )
    (
        playbook
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize()
            + cff.build_data_frame(b"a" * 16384).serialize(),
        )
        << SendData(
            tctx.client,
            cff.build_data_frame(b"a" * 16384).serialize(),
        )
        << SendData(
            tctx.client,
            cff.build_data_frame(b"a" * 16384).serialize(),
        )
        << SendData(
            tctx.client,
            cff.build_data_frame(b"a" * 16383).serialize(),
        )
        >> DataReceived(
            tctx.client,
            cff.build_window_update_frame(0, 65535).serialize()
            + cff.build_window_update_frame(1, 65535).serialize(),
        )
    )
    if trailers:
        assert (
            playbook
            << SendData(
                tctx.client,
                cff.build_data_frame(b"a" * 1).serialize(),
            )
            << SendData(tctx.client, cff.build_data_frame(b"a" * 4464).serialize())
            << SendData(
                tctx.client,
                cff.build_headers_frame(
                    example_response_trailers, flags=["END_STREAM"]
                ).serialize(),
            )
        )
    else:
        assert (
            playbook
            << SendData(
                tctx.client,
                cff.build_data_frame(b"a" * 1).serialize(),
            )
            << SendData(tctx.client, cff.build_data_frame(b"a" * 4464).serialize())
            << SendData(
                tctx.client,
                cff.build_data_frame(b"", flags=["END_STREAM"]).serialize(),
            )
        )
    assert flow().request.url == "http://example.com/"
    assert flow().response.text == "a" * 70000


@pytest.mark.parametrize("stream", ["stream", ""])
@pytest.mark.parametrize("when", ["request", "response"])
@pytest.mark.parametrize("how", ["RST", "disconnect", "RST+disconnect"])
def test_http2_client_aborts(tctx, stream, when, how):
    """
    Test handling of the case where a client aborts during request or response transmission.

    If the client aborts the request transmission, we must trigger an error hook,
    if the client disconnects during response transmission, no error hook is triggered.
    """
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook, cff = start_h2_client(tctx)
    resp = Placeholder(bytes)

    def enable_request_streaming(flow: HTTPFlow):
        flow.request.stream = True

    def enable_response_streaming(flow: HTTPFlow):
        flow.response.stream = True

    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_headers_frame(example_request_headers).serialize()
        )
        << http.HttpRequestHeadersHook(flow)
    )
    if stream and when == "request":
        assert (
            playbook
            >> reply(side_effect=enable_request_streaming)
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        )
    else:
        assert playbook >> reply()

    if when == "request":
        if "RST" in how:
            playbook >> DataReceived(
                tctx.client,
                cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize(),
            )
        else:
            playbook >> ConnectionClosed(tctx.client)
            playbook << CloseConnection(tctx.client)

        if stream:
            playbook << CloseConnection(server)
        playbook << http.HttpErrorHook(flow)
        playbook >> reply()

        if how == "RST+disconnect":
            playbook >> ConnectionClosed(tctx.client)
            playbook << CloseConnection(tctx.client)

        assert playbook
        assert (
            "stream reset" in flow().error.msg
            or "peer closed connection" in flow().error.msg
        )
        return

    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
        )
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> DataReceived(server, b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\n123")
        << http.HttpResponseHeadersHook(flow)
    )
    if stream:
        assert (
            playbook
            >> reply(side_effect=enable_response_streaming)
            << SendData(tctx.client, resp)
        )
    else:
        assert playbook >> reply()

    if "RST" in how:
        playbook >> DataReceived(
            tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
        )
    else:
        playbook >> ConnectionClosed(tctx.client)
        playbook << CloseConnection(tctx.client)

    playbook << CloseConnection(server)
    playbook << http.HttpErrorHook(flow)
    playbook >> reply()
    assert playbook

    if how == "RST+disconnect":
        playbook >> ConnectionClosed(tctx.client)
        playbook << CloseConnection(tctx.client)
        assert playbook

    if "RST" in how:
        assert "stream reset" in flow().error.msg
    else:
        assert "peer closed connection" in flow().error.msg


@pytest.mark.parametrize("normalize", [True, False])
def test_no_normalization(tctx, normalize):
    """Test that we don't normalize headers when we just pass them through."""
    tctx.options.normalize_outbound_headers = normalize
    tctx.options.validate_inbound_headers = False

    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook, cff = start_h2_client(tctx)

    request_headers = list(example_request_headers) + [
        (b"Should-Not-Be-Capitalized! ", b" :) ")
    ]
    request_headers_lower = [(k.lower(), v) for (k, v) in request_headers]
    response_headers = list(example_response_headers) + [(b"Same", b"Here")]
    response_headers_lower = [(k.lower(), v) for (k, v) in response_headers]

    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(request_headers, flags=["END_STREAM"]).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
    )
    frames = decode_frames(initial())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]
    assert (
        hpack.hpack.Decoder().decode(frames[2].data, True) == request_headers_lower
        if normalize
        else request_headers
    )

    sff = FrameFactory()
    (
        playbook
        >> DataReceived(
            server,
            sff.build_headers_frame(response_headers, flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        << http.HttpResponseHook(flow)
        >> reply()
    )
    if normalize:
        playbook << Log(
            "Lowercased 'Same' header as uppercase is not allowed with HTTP/2."
        )
    hdrs = response_headers_lower if normalize else response_headers
    assert playbook << SendData(
        tctx.client, cff.build_headers_frame(hdrs, flags=["END_STREAM"]).serialize()
    )

    assert flow().request.headers.fields == ((b"Should-Not-Be-Capitalized! ", b" :) "),)
    assert flow().response.headers.fields == ((b"Same", b"Here"),)


@pytest.mark.parametrize("stream", ["stream", ""])
def test_end_stream_via_headers(tctx, stream):
    playbook, cff = start_h2_client(tctx)
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    sff = FrameFactory()
    forwarded_request_frames = Placeholder(bytes)
    forwarded_response_frames = Placeholder(bytes)

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = bool(stream)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, forwarded_request_frames)
        >> DataReceived(
            server,
            sff.build_headers_frame(
                example_response_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(tctx.client, forwarded_response_frames)
    )

    frames = decode_frames(forwarded_request_frames())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]
    assert "END_STREAM" in frames[2].flags

    frames = decode_frames(forwarded_response_frames())
    assert [type(x) for x in frames] == [
        hyperframe.frame.HeadersFrame,
    ]
    assert "END_STREAM" in frames[0].flags


@pytest.mark.parametrize(
    "input,pseudo,headers",
    [
        ([(b"foo", b"bar")], {}, {"foo": "bar"}),
        ([(b":status", b"418")], {b":status": b"418"}, {}),
        (
            [(b":status", b"418"), (b"foo", b"bar")],
            {b":status": b"418"},
            {"foo": "bar"},
        ),
    ],
)
def test_split_pseudo_headers(input, pseudo, headers):
    actual_pseudo, actual_headers = split_pseudo_headers(input)
    assert pseudo == actual_pseudo
    assert Headers(**headers) == actual_headers


def test_split_pseudo_headers_err():
    with pytest.raises(ValueError, match="Duplicate HTTP/2 pseudo header"):
        split_pseudo_headers([(b":status", b"418"), (b":status", b"418")])


def test_rst_then_close(tctx):
    """
    Test that we properly handle the case of a client that first causes protocol errors and then disconnects.

    Adapted from h2spec http2/5.1/5.
    """
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> DataReceived(
            tctx.client, cff.build_data_frame(b"unexpected data frame").serialize()
        )
        << SendData(
            tctx.client,
            cff.build_rst_stream_frame(1, ErrorCodes.STREAM_CLOSED).serialize(),
        )
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.client)
        >> reply("connection cancelled", to=-5)
        << http.HttpErrorHook(flow)
        >> reply()
    )
    assert flow().error.msg == "connection cancelled"


def test_cancel_then_server_disconnect(tctx):
    """
    Test that we properly handle the case of the following event sequence:
        - client cancels a stream
        - we start an error hook
        - server disconnects
        - error hook completes.
    """
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> DataReceived(
            tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
        )
        << CloseConnection(server)
        << http.HttpErrorHook(flow)
        >> reply()
        >> ConnectionClosed(server)
        << None
    )


def test_cancel_during_response_hook(tctx):
    """
    Test that we properly handle the case of the following event sequence:
        - we receive a server response
        - we trigger the response hook
        - the client cancels the stream
        - the response hook completes

    Given that we have already triggered the response hook, we don't want to trigger the error hook.
    """
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None)
        << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        >> DataReceived(server, b"HTTP/1.1 204 No Content\r\n\r\n")
        << http.HttpResponseHeadersHook(flow)
        << CloseConnection(server)
        >> reply(to=-2)
        << http.HttpResponseHook(flow)
        >> DataReceived(
            tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
        )
        >> reply(to=-2)
    )


def test_http_1_1_required(tctx):
    """
    Test that we properly forward an HTTP_1_1_REQUIRED stream error.
    """
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    forwarded_request_frames = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, forwarded_request_frames)
        >> DataReceived(
            server,
            sff.build_rst_stream_frame(1, ErrorCodes.HTTP_1_1_REQUIRED).serialize(),
        )
        << http.HttpErrorHook(flow)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_rst_stream_frame(1, ErrorCodes.HTTP_1_1_REQUIRED).serialize(),
        )
    )


def test_stream_concurrency(tctx):
    """Test that we can send an intercepted request with a lower stream id than one that has already been sent."""
    playbook, cff = start_h2_client(tctx)
    flow1 = Placeholder(HTTPFlow)
    flow2 = Placeholder(HTTPFlow)

    reqheadershook1 = http.HttpRequestHeadersHook(flow1)
    reqheadershook2 = http.HttpRequestHeadersHook(flow2)
    reqhook1 = http.HttpRequestHook(flow1)
    reqhook2 = http.HttpRequestHook(flow2)

    server = Placeholder(Server)
    data_req1 = Placeholder(bytes)
    data_req2 = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize()
            + cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        << reqheadershook1
        << reqheadershook2
        >> reply(to=reqheadershook1)
        << reqhook1
        >> reply(to=reqheadershook2)
        << reqhook2
        # req 2 overtakes 1 and we already have a reply:
        >> reply(to=reqhook2)
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, data_req2)
        >> reply(to=reqhook1)
        << SendData(server, data_req1)
    )
    frames = decode_frames(data_req2())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]
    frames = decode_frames(data_req1())
    assert [type(x) for x in frames] == [
        hyperframe.frame.HeadersFrame,
    ]


def test_max_concurrency(tctx):
    playbook, cff = start_h2_client(tctx)
    server = Placeholder(Server)
    req1_bytes = Placeholder(bytes)
    settings_ack_bytes = Placeholder(bytes)
    req2_bytes = Placeholder(bytes)
    playbook.hooks = False
    sff = FrameFactory()

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize(),
        )
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, req1_bytes)
        >> DataReceived(
            server,
            sff.build_settings_frame(
                {h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 1}
            ).serialize(),
        )
        << SendData(server, settings_ack_bytes)
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        # Can't send it upstream yet, all streams in use!
        >> DataReceived(
            server,
            sff.build_headers_frame(
                example_response_headers, flags=["END_STREAM"], stream_id=1
            ).serialize(),
        )
        # But now we can!
        << SendData(server, req2_bytes)
        << SendData(tctx.client, Placeholder(bytes))
        >> DataReceived(
            server,
            sff.build_headers_frame(
                example_response_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        << SendData(tctx.client, Placeholder(bytes))
    )
    settings, _, req1 = decode_frames(req1_bytes())
    (settings_ack,) = decode_frames(settings_ack_bytes())
    (req2,) = decode_frames(req2_bytes())

    assert type(settings) is hyperframe.frame.SettingsFrame
    assert type(req1) is hyperframe.frame.HeadersFrame
    assert type(settings_ack) is hyperframe.frame.SettingsFrame
    assert type(req2) is hyperframe.frame.HeadersFrame
    assert req1.stream_id == 1
    assert req2.stream_id == 3


def test_stream_concurrent_get_connection(tctx):
    """Test that an immediate second request for the same domain does not trigger a second connection attempt."""
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False

    server = Placeholder(Server)
    data = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize(),
        )
        << (o := OpenConnection(server))
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        >> reply(None, to=o, side_effect=make_h2)
        << SendData(server, data)
    )
    frames = decode_frames(data())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
        hyperframe.frame.HeadersFrame,
    ]


def test_kill_stream(tctx):
    """Test that we can kill individual streams."""
    playbook, cff = start_h2_client(tctx)
    flow1 = Placeholder(HTTPFlow)
    flow2 = Placeholder(HTTPFlow)

    req_headers_hook_1 = http.HttpRequestHeadersHook(flow1)

    def kill(flow: HTTPFlow):
        # Can't use flow.kill() here because that currently still depends on a reply object.
        flow.error = Error(Error.KILLED_MESSAGE)

    server = Placeholder(Server)
    data_req1 = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize()
            + cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        << req_headers_hook_1
        << http.HttpRequestHeadersHook(flow2)
        >> reply(side_effect=kill)
        << http.HttpErrorHook(flow2)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_rst_stream_frame(
                3, error_code=ErrorCodes.INTERNAL_ERROR
            ).serialize(),
        )
        >> reply(to=req_headers_hook_1)
        << http.HttpRequestHook(flow1)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, data_req1)
    )
    frames = decode_frames(data_req1())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]


class TestClient:
    def test_no_data_on_closed_stream(self, tctx):
        tctx.options.http2_ping_keepalive = 0
        frame_factory = FrameFactory()
        req = Request.make("GET", "http://example.com/")
        resp = {":status": 200}
        assert (
            Playbook(Http2Client(tctx))
            << SendData(
                tctx.server, Placeholder(bytes)
            )  # preamble + initial settings frame
            >> DataReceived(
                tctx.server,
                frame_factory.build_settings_frame({}, ack=True).serialize(),
            )
            >> http.RequestHeaders(1, req, end_stream=True)
            << SendData(
                tctx.server,
                b"\x00\x00\x06\x01\x05\x00\x00\x00\x01\x82\x86\x84\\\x81\x07",
            )
            >> http.RequestEndOfMessage(1)
            >> DataReceived(
                tctx.server, frame_factory.build_headers_frame(resp).serialize()
            )
            << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
            >> http.RequestProtocolError(
                1, "cancelled", code=ErrorCode.CLIENT_DISCONNECTED
            )
            << SendData(
                tctx.server,
                frame_factory.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize(),
            )
            >> DataReceived(
                tctx.server, frame_factory.build_data_frame(b"foo").serialize()
            )
            << SendData(
                tctx.server,
                frame_factory.build_rst_stream_frame(
                    1, ErrorCodes.STREAM_CLOSED
                ).serialize(),
            )
        )  # important: no ResponseData event here!

    @pytest.mark.parametrize(
        "code,log_msg",
        [
            (b"103", "103 Early Hints"),
            (b"1not_a_number", "<unknown status> "),
        ],
    )
    def test_informational_response(self, tctx, code, log_msg):
        tctx.options.http2_ping_keepalive = 0
        frame_factory = FrameFactory()
        req = Request.make("GET", "http://example.com/")
        resp = {":status": code}
        assert (
            Playbook(Http2Client(tctx), logs=True)
            << SendData(
                tctx.server, Placeholder(bytes)
            )  # preamble + initial settings frame
            >> http.RequestHeaders(1, req, end_stream=True)
            << SendData(
                tctx.server,
                b"\x00\x00\x06\x01\x05\x00\x00\x00\x01\x82\x86\x84\\\x81\x07",
            )
            >> DataReceived(
                tctx.server, frame_factory.build_headers_frame(resp).serialize()
            )
            << Log(f"Swallowing HTTP/2 informational response: {log_msg}")
        )


def test_early_server_data(tctx):
    playbook, cff = start_h2_client(tctx)
    sff = FrameFactory()

    tctx.server.address = ("example.com", 80)
    tctx.server.state = ConnectionState.OPEN
    tctx.server.alpn = b"h2"

    flow = Placeholder(HTTPFlow)
    server1 = Placeholder(bytes)
    server2 = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << (h := http.HttpRequestHook(flow))
        # Surprise! We get data from the server before the request hook finishes.
        >> DataReceived(tctx.server, sff.build_settings_frame({}).serialize())
        << SendData(tctx.server, server1)
        # Request hook finishes...
        >> reply(to=h)
        << SendData(tctx.server, server2)
    )
    assert [type(x) for x in decode_frames(server1())] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.SettingsFrame,
    ]
    assert [type(x) for x in decode_frames(server2())] == [
        hyperframe.frame.HeadersFrame,
    ]


def test_request_smuggling_cl(tctx):
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False
    err = Placeholder(bytes)

    headers = (
        (b":method", b"POST"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"example.com"),
        (b"content-length", b"3"),
    )

    assert (
        playbook
        >> DataReceived(tctx.client, cff.build_headers_frame(headers).serialize())
        >> DataReceived(
            tctx.client,
            cff.build_data_frame(
                b"abcPOST / HTTP/1.1 ...", flags=["END_STREAM"]
            ).serialize(),
        )
        << SendData(tctx.client, err)
        << CloseConnection(tctx.client)
    )
    assert b"InvalidBodyLengthError" in err()


def test_request_smuggling_te(tctx):
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False
    err = Placeholder(bytes)

    headers = (
        (b":method", b"POST"),
        (b":scheme", b"http"),
        (b":path", b"/"),
        (b":authority", b"example.com"),
        (b"transfer-encoding", b"chunked"),
    )

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(headers, flags=["END_STREAM"]).serialize(),
        )
        << SendData(tctx.client, err)
        << CloseConnection(tctx.client)
    )
    assert b"Connection-specific header field present" in err()


def test_request_keepalive(tctx, monkeypatch):
    playbook, cff = start_h2_client(tctx, 58)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    initial = Placeholder(bytes)

    def advance_time(_):
        t = time.time()
        monkeypatch.setattr(time, "time", lambda: t + 60)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << RequestWakeup(58)
        << SendData(server, initial)
        >> reply(to=-2, side_effect=advance_time)
        << SendData(
            server, b"\x00\x00\x08\x06\x00\x00\x00\x00\x0000000000"
        )  # ping frame
        << RequestWakeup(58)
    )


def test_keepalive_disconnect(tctx, monkeypatch):
    playbook, cff = start_h2_client(tctx, 58)
    playbook.hooks = False
    sff = FrameFactory()
    server = Placeholder(Server)
    wakeup_command = RequestWakeup(58)

    http_response = (
        sff.build_headers_frame(example_response_headers).serialize()
        + sff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
    )

    def advance_time(_):
        t = time.time()
        monkeypatch.setattr(time, "time", lambda: t + 60)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << wakeup_command
        << SendData(server, Placeholder(bytes))
        >> DataReceived(server, http_response)
        << SendData(tctx.client, Placeholder(bytes))
        >> ConnectionClosed(server)
        << CloseConnection(server)
        >> reply(to=wakeup_command, side_effect=advance_time)
        << None
    )


def test_alt_svc(tctx):
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    initial = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
        >> DataReceived(
            server, cff.build_alt_svc_frame(0, b"example.com", b'h3=":443"').serialize()
        )
        << Log("Received HTTP/2 Alt-Svc frame, which will not be forwarded.", DEBUG)
    )


def test_no_extra_empty_data_frame(tctx):
    """Ensure we don't send empty data frames without EOS bit set when streaming, https://github.com/mitmproxy/mitmproxy/pull/7480"""
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    def enable_streaming(flow: HTTPFlow) -> None:
        if flow.response:
            flow.response.stream = True
        else:
            flow.request.stream = True

    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_headers_frame(example_request_headers).serialize()
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
    )
    initial_frames = decode_frames(initial())
    assert [type(x) for x in initial_frames] == [
        hyperframe.frame.SettingsFrame,
        hyperframe.frame.WindowUpdateFrame,
        hyperframe.frame.HeadersFrame,
    ]

    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
        )
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(server, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize())
        >> DataReceived(
            server, cff.build_headers_frame(example_response_headers).serialize()
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << SendData(
            tctx.client, cff.build_headers_frame(example_response_headers).serialize()
        )
        >> DataReceived(
            server, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
        )
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(
            tctx.client, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
        )
    )


def test_forward_empty_data_frame(tctx):
    """Ensure that we preserve empty data frames, https://github.com/mitmproxy/mitmproxy/pull/7480"""
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    def enable_streaming(flow: HTTPFlow) -> None:
        if flow.response:
            flow.response.stream = True
        else:
            flow.request.stream = True

    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_headers_frame(example_request_headers).serialize()
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
        # Empty data frame from client
        >> DataReceived(tctx.client, cff.build_data_frame(b"").serialize())
        << SendData(server, cff.build_data_frame(b"").serialize())
        >> DataReceived(
            tctx.client, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
        )
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(server, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize())
        >> DataReceived(
            server, cff.build_headers_frame(example_response_headers).serialize()
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
        << SendData(
            tctx.client, cff.build_headers_frame(example_response_headers).serialize()
        )
        # Empty data frame from server
        >> DataReceived(server, cff.build_data_frame(b"").serialize())
        << SendData(tctx.client, cff.build_data_frame(b"").serialize())
    )


h2_supports_draining = hasattr(h2.connection.H2ConnectionStateMachine(), "draining")
requires_h2_draining = pytest.mark.skipif(
    not h2_supports_draining, reason="h2 without graceful GOAWAY support"
)


def start_h2_request(
    tctx: Context, cff: FrameFactory, playbook: Playbook, flow, server, stream_id=1
) -> Placeholder:
    """Send a GET from the client and let mitmproxy forward it on a new HTTP/2 server connection."""
    initial = Placeholder(bytes)
    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=stream_id
            ).serialize(),
        )
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, initial)
    )
    return initial


@requires_h2_draining
def test_graceful_goaway_completes_open_stream(tctx):
    """
    A server's graceful GOAWAY, followed by a PING (RFC 9113 two-stage shutdown),
    lets the in-flight response complete. We acknowledge the PING, finish the stream,
    then send our own GOAWAY and close the server connection.
    """
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    start_h2_request(tctx, cff, playbook, flow, server)

    assert (
        playbook
        >> DataReceived(
            server, sff.build_headers_frame(example_response_headers).serialize()
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        >> DataReceived(
            server,
            sff.build_goaway_frame(last_stream_id=2**31 - 1).serialize()
            + sff.build_ping_frame(b"12345678").serialize(),
        )
        << SendData(
            server, sff.build_ping_frame(b"12345678", flags=["ACK"]).serialize()
        )
        >> DataReceived(
            server,
            sff.build_data_frame(b"Hello, World!", flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHook(flow)
        # the last stream is done: we send our own GOAWAY and close.
        << SendData(server, sff.build_goaway_frame(last_stream_id=0).serialize())
        << CloseConnection(server)
        >> reply(to=-3)
        << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize()
            + cff.build_data_frame(b"Hello, World!").serialize()
            + cff.build_data_frame(b"", flags=["END_STREAM"]).serialize(),
        )
    )
    assert flow().response.text == "Hello, World!"
    assert flow().error is None


def finish_response(tctx, cff, sff, playbook, flow, server, stream_id=1):
    """Let the server answer stream 1 in full and check that the client gets it."""
    assert (
        playbook
        >> DataReceived(
            server,
            sff.build_headers_frame(example_response_headers).serialize()
            + sff.build_data_frame(b"ok", flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_headers_frame(
                example_response_headers, stream_id=stream_id
            ).serialize()
            + cff.build_data_frame(b"ok", stream_id=stream_id).serialize()
            + cff.build_data_frame(
                b"", flags=["END_STREAM"], stream_id=stream_id
            ).serialize(),
        )
    )


@requires_h2_draining
def test_graceful_goaway_idle_connection(tctx):
    """A server retires an idle connection: we acknowledge the PING, send GOAWAY and close."""
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    start_h2_request(tctx, cff, playbook, flow, server)
    finish_response(tctx, cff, sff, playbook, flow, server)

    assert (
        playbook
        >> DataReceived(
            server,
            sff.build_goaway_frame(last_stream_id=2**31 - 1).serialize()
            + sff.build_ping_frame(b"12345678").serialize(),
        )
        << SendData(
            server, sff.build_ping_frame(b"12345678", flags=["ACK"]).serialize()
        )
        << SendData(server, sff.build_goaway_frame(last_stream_id=0).serialize())
        << CloseConnection(server)
    )


@requires_h2_draining
def test_graceful_goaway_new_request_uses_new_connection(tctx):
    """While a connection drains, a new request opens a new server connection."""
    playbook, cff = start_h2_client(tctx)
    flow1 = Placeholder(HTTPFlow)
    flow2 = Placeholder(HTTPFlow)
    server1 = Placeholder(Server)
    server2 = Placeholder(Server)
    sff = FrameFactory()
    start_h2_request(tctx, cff, playbook, flow1, server1)

    assert (
        playbook
        >> DataReceived(
            server1,
            sff.build_headers_frame(example_response_headers).serialize()
            + sff.build_goaway_frame(last_stream_id=1).serialize(),
        )
        << http.HttpResponseHeadersHook(flow1)
        >> reply()
    )
    start_h2_request(tctx, cff, playbook, flow2, server2, stream_id=3)
    assert server1() is not server2()
    assert server1().connected


def test_goaway_with_error_closes_connection(tctx):
    """A GOAWAY with an error code still tears down the connection and fails open streams."""
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    start_h2_request(tctx, cff, playbook, flow, server)

    assert (
        playbook
        >> DataReceived(
            server,
            sff.build_goaway_frame(
                last_stream_id=1, error_code=ErrorCodes.INTERNAL_ERROR
            ).serialize(),
        )
        << CloseConnection(server)
        << http.HttpErrorHook(flow)
        >> reply()
        << SendData(tctx.client, Placeholder(bytes))
    )
    assert "HTTP/2 connection closed" in flow().error.msg


@requires_h2_draining
def test_graceful_goaway_fails_unprocessed_streams(tctx):
    """
    Streams above the GOAWAY's last stream id were never processed by the server:
    they fail at once, while the stream at or below it completes.
    """
    playbook, cff = start_h2_client(tctx)
    flow1 = Placeholder(HTTPFlow)
    flow2 = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    to_server = Placeholder(bytes)
    to_client = Placeholder(bytes)
    reqheadershook1 = http.HttpRequestHeadersHook(flow1)
    reqheadershook2 = http.HttpRequestHeadersHook(flow2)
    reqhook1 = http.HttpRequestHook(flow1)
    reqhook2 = http.HttpRequestHook(flow2)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize()
            + cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        << reqheadershook1
        << reqheadershook2
        >> reply(to=reqheadershook1)
        << reqhook1
        >> reply(to=reqheadershook2)
        << reqhook2
        >> reply(to=reqhook1)
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, Placeholder(bytes))
        >> reply(to=reqhook2)
        << SendData(server, Placeholder(bytes))
        # The server processed stream 1 only.
        >> DataReceived(server, sff.build_goaway_frame(last_stream_id=1).serialize())
        << http.HttpErrorHook(flow2)
        << SendData(server, to_server)
        >> reply(to=-2)
        << SendData(tctx.client, to_client)
    )
    assert [type(f) for f in decode_frames(to_server())] == [
        hyperframe.frame.RstStreamFrame
    ]
    assert decode_frames(to_server())[0].stream_id == 3
    assert decode_frames(to_server())[0].error_code == ErrorCodes.CANCEL
    assert "HTTP/2 connection closed" in flow2().error.msg
    client_frames = decode_frames(to_client())
    assert {f.stream_id for f in client_frames} == {3}
    assert flow1().error is None

    assert (
        playbook
        >> DataReceived(
            server,
            sff.build_headers_frame(example_response_headers).serialize()
            + sff.build_data_frame(b"ok", flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHeadersHook(flow1)
        # stream 1 was the last one and has ended: we send our own GOAWAY and close.
        << SendData(server, sff.build_goaway_frame(last_stream_id=0).serialize())
        << CloseConnection(server)
        >> reply(to=-3)
        << http.HttpResponseHook(flow1)
        >> reply()
        << SendData(tctx.client, Placeholder(bytes))
    )
    assert flow1().response.text == "ok"
    assert flow1().error is None


@requires_h2_draining
def test_graceful_goaway_client_layer(tctx):
    """
    Http2Client signals the drain to the HTTP layer, refuses a stream that got the
    connection just before the GOAWAY, and closes once the last open stream is reset.
    """
    from mitmproxy.proxy.layers.http._base import DrainHttpConnection

    tctx.options.http2_ping_keepalive = 0
    ff = FrameFactory()
    req = Request.make("GET", "http://example.com/")
    refused = Placeholder(http.ResponseProtocolError)
    assert (
        Playbook(Http2Client(tctx))
        << SendData(tctx.server, Placeholder(bytes))
        >> DataReceived(tctx.server, ff.build_settings_frame({}, ack=True).serialize())
        >> http.RequestHeaders(1, req, end_stream=True)
        << SendData(tctx.server, Placeholder(bytes))
        >> DataReceived(
            tctx.server, ff.build_goaway_frame(last_stream_id=1).serialize()
        )
        << DrainHttpConnection(tctx.server)
        >> http.RequestHeaders(3, req, end_stream=True)
        << http.ReceiveHttp(refused)
        >> http.RequestProtocolError(1, "cancelled", code=ErrorCode.CLIENT_DISCONNECTED)
        << SendData(
            tctx.server, ff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
        )
        << SendData(tctx.server, ff.build_goaway_frame(last_stream_id=0).serialize())
        << CloseConnection(tctx.server)
    )
    assert refused().stream_id == 3
    assert "GOAWAY" in refused().message


@requires_h2_draining
def test_graceful_goaway_fails_queued_streams(tctx):
    """Requests waiting for a free stream fail when the connection starts draining."""
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False
    server = Placeholder(Server)
    sff = FrameFactory()
    error_response = Placeholder(bytes)

    assert (
        playbook
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=1
            ).serialize(),
        )
        << OpenConnection(server)
        >> reply(None, side_effect=make_h2)
        << SendData(server, Placeholder(bytes))
        >> DataReceived(
            server,
            sff.build_settings_frame(
                {h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 1}
            ).serialize(),
        )
        << SendData(server, Placeholder(bytes))
        >> DataReceived(
            tctx.client,
            cff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"], stream_id=3
            ).serialize(),
        )
        # stream 3 is queued: all streams are in use.
        >> DataReceived(server, sff.build_goaway_frame(last_stream_id=1).serialize())
        << SendData(tctx.client, error_response)
    )
    frames = decode_frames(error_response())
    assert {f.stream_id for f in frames} == {3}
    body = b"".join(f.data for f in frames if isinstance(f, hyperframe.frame.DataFrame))
    assert b"502 Bad Gateway" in body
    assert b"shutting down (GOAWAY)" in body


@requires_h2_draining
class TestGracefulGoAwayClient:
    """Http2Client while a server connection drains (direct layer tests)."""

    def start(self, tctx, settings=None) -> tuple[Playbook, FrameFactory]:
        tctx.options.http2_ping_keepalive = 0
        ff = FrameFactory()
        playbook = Playbook(Http2Client(tctx))
        assert playbook << SendData(tctx.server, Placeholder(bytes))
        if settings is not None:
            assert (
                playbook
                >> DataReceived(
                    tctx.server, ff.build_settings_frame(settings).serialize()
                )
                << SendData(
                    tctx.server, ff.build_settings_frame({}, ack=True).serialize()
                )
            )
        return playbook, ff

    @pytest.mark.parametrize("trailers", [False, True])
    def test_buffered_upload_completes(self, tctx, trailers):
        """Request body (and trailers) held back by flow control are still sent after a graceful GOAWAY."""
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        playbook, ff = self.start(
            tctx, {h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: 10}
        )
        req = Request.make("POST", "http://example.com/upload")
        rest = Placeholder(bytes)
        assert (
            playbook
            >> http.RequestHeaders(1, req, end_stream=False)
            << SendData(tctx.server, Placeholder(bytes))
            >> http.RequestData(1, b"x" * 30)
            << SendData(tctx.server, ff.build_data_frame(b"x" * 10).serialize())
        )
        if trailers:
            assert playbook >> http.RequestTrailers(
                1, Headers(example_request_trailers)
            )
        assert (
            playbook
            >> http.RequestEndOfMessage(1)
            >> DataReceived(
                tctx.server, ff.build_goaway_frame(last_stream_id=1).serialize()
            )
            << DrainHttpConnection(tctx.server)
            >> DataReceived(
                tctx.server, ff.build_window_update_frame(1, 100).serialize()
            )
            << SendData(tctx.server, rest)
            >> DataReceived(
                tctx.server,
                ff.build_headers_frame(
                    example_response_headers, flags=["END_STREAM"]
                ).serialize(),
            )
            << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
            << http.ReceiveHttp(http.ResponseEndOfMessage(1))
            << SendData(
                tctx.server, ff.build_goaway_frame(last_stream_id=0).serialize()
            )
            << CloseConnection(tctx.server)
        )
        if trailers:
            data, end = decode_frames(rest())
            assert data.data == b"x" * 20 and "END_STREAM" not in data.flags
            assert isinstance(end, hyperframe.frame.HeadersFrame)
            assert "END_STREAM" in end.flags
        else:
            data, end = decode_frames(rest())
            assert data.data == b"x" * 20
            assert end.data == b"" and "END_STREAM" in end.flags

    def test_goaway_and_reset_in_one_read(self, tctx):
        """
        GOAWAY(last=1) and RST_STREAM for the unprocessed stream in one read: the
        stream fails exactly once, under the client's stream id, and is not reset again.
        """
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        playbook, ff = self.start(tctx, {})
        req = Request.make("GET", "http://example.com/")
        failed = Placeholder(http.ResponseProtocolError)
        assert (
            playbook
            >> http.RequestHeaders(5, req, end_stream=True)  # our stream 1
            << SendData(tctx.server, Placeholder(bytes))
            >> http.RequestHeaders(7, req, end_stream=True)  # our stream 3
            << SendData(tctx.server, Placeholder(bytes))
            >> DataReceived(
                tctx.server,
                ff.build_goaway_frame(last_stream_id=1).serialize()
                + ff.build_rst_stream_frame(3, ErrorCodes.REFUSED_STREAM).serialize(),
            )
            << DrainHttpConnection(tctx.server)
            << http.ReceiveHttp(failed)
            >> DataReceived(
                tctx.server,
                ff.build_headers_frame(
                    example_response_headers, flags=["END_STREAM"]
                ).serialize(),
            )
            << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
            << http.ReceiveHttp(http.ResponseEndOfMessage(5))
            << SendData(
                tctx.server, ff.build_goaway_frame(last_stream_id=0).serialize()
            )
            << CloseConnection(tctx.server)
        )
        assert failed().stream_id == 7

    def test_retired_stream_frames_in_same_read(self, tctx):
        """
        A server sends GOAWAY(last=1), then a response for the unprocessed stream 3
        and a full response for stream 1, all in one read (#7879). Stream 3 fails
        once; its later frames are dropped (DATA is still acknowledged); stream 1
        completes; we close gracefully, not with PROTOCOL_ERROR.
        """
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        playbook, ff = self.start(tctx, {})
        req = Request.make("GET", "http://example.com/")
        failed = Placeholder(http.ResponseProtocolError)
        response = Placeholder(http.ResponseHeaders)
        to_server = Placeholder(bytes)
        h2_conn = playbook.layer.h2_conn
        acknowledged = []
        acknowledge = h2_conn.acknowledge_received_data

        def record(size, stream_id):
            acknowledged.append((stream_id, size))
            acknowledge(size, stream_id)

        h2_conn.acknowledge_received_data = record
        assert (
            playbook
            >> http.RequestHeaders(5, req, end_stream=True)  # our stream 1
            << SendData(tctx.server, Placeholder(bytes))
            >> http.RequestHeaders(7, req, end_stream=True)  # our stream 3
            << SendData(tctx.server, Placeholder(bytes))
            >> DataReceived(
                tctx.server,
                ff.build_goaway_frame(last_stream_id=1).serialize()
                + ff.build_headers_frame(
                    example_response_headers, stream_id=3
                ).serialize()
                + ff.build_data_frame(b"late", stream_id=3).serialize()
                + ff.build_headers_frame(
                    example_response_trailers, flags=["END_STREAM"], stream_id=3
                ).serialize()
                + ff.build_headers_frame(
                    example_response_headers, stream_id=1
                ).serialize()
                + ff.build_data_frame(
                    b"ok", flags=["END_STREAM"], stream_id=1
                ).serialize(),
            )
            << DrainHttpConnection(tctx.server)
            << http.ReceiveHttp(failed)
            << http.ReceiveHttp(response)
            << http.ReceiveHttp(http.ResponseData(5, b"ok"))
            << http.ReceiveHttp(http.ResponseEndOfMessage(5))
            << SendData(tctx.server, to_server)
            << CloseConnection(tctx.server)
        )
        assert failed().stream_id == 7
        assert response().stream_id == 5
        # the retired stream's DATA still counts toward connection flow control.
        assert acknowledged == [(3, 4), (1, 2)]
        frames = decode_frames(to_server())
        goaways = [f for f in frames if isinstance(f, hyperframe.frame.GoAwayFrame)]
        assert [g.error_code for g in goaways] == [ErrorCodes.NO_ERROR]
        # stream 3 already ended in this read, so it needs no RST_STREAM.
        assert not any(isinstance(f, hyperframe.frame.RstStreamFrame) for f in frames)

    def test_two_stage_goaway(self, tctx):
        """The first GOAWAY (2**31-1) fails nothing; the second fails streams above its boundary."""
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        playbook, ff = self.start(tctx, {})
        req = Request.make("GET", "http://example.com/")
        failed = Placeholder(http.ResponseProtocolError)
        reset = Placeholder(bytes)
        assert (
            playbook
            >> http.RequestHeaders(1, req, end_stream=True)
            << SendData(tctx.server, Placeholder(bytes))
            >> http.RequestHeaders(3, req, end_stream=True)
            << SendData(tctx.server, Placeholder(bytes))
            >> DataReceived(
                tctx.server,
                ff.build_goaway_frame(last_stream_id=2**31 - 1).serialize()
                + ff.build_ping_frame(b"12345678").serialize(),
            )
            << DrainHttpConnection(tctx.server)
            << SendData(
                tctx.server, ff.build_ping_frame(b"12345678", flags=["ACK"]).serialize()
            )
            >> DataReceived(
                tctx.server, ff.build_goaway_frame(last_stream_id=1).serialize()
            )
            << http.ReceiveHttp(failed)
            << SendData(tctx.server, reset)
        )
        assert failed().stream_id == 3
        (rst,) = decode_frames(reset())
        assert isinstance(rst, hyperframe.frame.RstStreamFrame)
        assert rst.stream_id == 3

    def test_response_done_before_request_body(self, tctx):
        """The connection stays open until the request body is sent, then closes."""
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        playbook, ff = self.start(tctx, {})
        req = Request.make("POST", "http://example.com/")
        assert (
            playbook
            >> http.RequestHeaders(1, req, end_stream=False)
            << SendData(tctx.server, Placeholder(bytes))
            >> DataReceived(
                tctx.server,
                ff.build_goaway_frame(last_stream_id=1).serialize()
                + ff.build_headers_frame(
                    example_response_headers, flags=["END_STREAM"]
                ).serialize(),
            )
            << DrainHttpConnection(tctx.server)
            << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
            << http.ReceiveHttp(http.ResponseEndOfMessage(1))
            >> http.RequestData(1, b"body")
            << SendData(tctx.server, ff.build_data_frame(b"body").serialize())
            >> http.RequestEndOfMessage(1)
            << SendData(
                tctx.server, ff.build_data_frame(b"", flags=["END_STREAM"]).serialize()
            )
            << SendData(
                tctx.server, ff.build_goaway_frame(last_stream_id=0).serialize()
            )
            << CloseConnection(tctx.server)
        )

    def test_keepalive_while_draining_and_after_close(self, tctx, monkeypatch):
        """Keepalive PINGs continue while draining; wakeups after the close are ignored."""
        from mitmproxy.proxy.layers.http._base import DrainHttpConnection

        tctx.options.http2_ping_keepalive = 58
        ff = FrameFactory()
        req = Request.make("GET", "http://example.com/")

        def advance_time(_):
            t = time.time()
            monkeypatch.setattr(time, "time", lambda: t + 60)

        wakeup = RequestWakeup(58)
        assert (
            Playbook(Http2Client(tctx))
            << wakeup
            << SendData(tctx.server, Placeholder(bytes))
            >> http.RequestHeaders(1, req, end_stream=True)
            << SendData(tctx.server, Placeholder(bytes))
            >> DataReceived(
                tctx.server, ff.build_goaway_frame(last_stream_id=1).serialize()
            )
            << DrainHttpConnection(tctx.server)
            >> reply(to=wakeup, side_effect=advance_time)
            << SendData(tctx.server, ff.build_ping_frame(b"0" * 8).serialize())
            << RequestWakeup(58)
            >> DataReceived(
                tctx.server,
                ff.build_headers_frame(
                    example_response_headers, flags=["END_STREAM"]
                ).serialize(),
            )
            << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
            << http.ReceiveHttp(http.ResponseEndOfMessage(1))
            << SendData(
                tctx.server, ff.build_goaway_frame(last_stream_id=0).serialize()
            )
            << CloseConnection(tctx.server)
            >> reply(to=wakeup)
            << None
        )


@requires_h2_draining
def test_graceful_goaway_from_client(tctx):
    """A client's graceful GOAWAY lets its pending response finish; then we close."""
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    sff = FrameFactory()
    start_h2_request(tctx, cff, playbook, flow, server)

    assert (
        playbook
        >> DataReceived(
            tctx.client, cff.build_goaway_frame(last_stream_id=0).serialize()
        )
        >> DataReceived(
            server,
            sff.build_headers_frame(example_response_headers).serialize()
            + sff.build_data_frame(b"ok", flags=["END_STREAM"]).serialize(),
        )
        << http.HttpResponseHeadersHook(flow)
        >> reply()
        << http.HttpResponseHook(flow)
        >> reply()
        << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize()
            + cff.build_data_frame(b"ok").serialize()
            + cff.build_data_frame(b"", flags=["END_STREAM"]).serialize(),
        )
        << SendData(tctx.client, cff.build_goaway_frame(last_stream_id=1).serialize())
        << CloseConnection(tctx.client)
    )
    assert flow().response.text == "ok"


@requires_h2_draining
def test_graceful_goaway_from_client_buffered_response(tctx):
    """A response held back by the client's flow control still completes after its graceful GOAWAY."""
    from mitmproxy.proxy.layers.http._base import DrainHttpConnection
    from mitmproxy.proxy.layers.http._http2 import Http2Server

    tctx.client.alpn = b"h2"
    ff = FrameFactory()
    resp = Response.make(200)
    rest = Placeholder(bytes)
    assert (
        Playbook(Http2Server(tctx))
        << SendData(tctx.client, Placeholder(bytes))
        >> DataReceived(
            tctx.client,
            ff.preamble()
            + ff.build_settings_frame(
                {h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: 10}
            ).serialize(),
        )
        << SendData(tctx.client, ff.build_settings_frame({}, ack=True).serialize())
        >> DataReceived(
            tctx.client,
            ff.build_headers_frame(
                example_request_headers, flags=["END_STREAM"]
            ).serialize(),
        )
        << http.ReceiveHttp(Placeholder(http.RequestHeaders))
        << http.ReceiveHttp(http.RequestEndOfMessage(1))
        >> http.ResponseHeaders(1, resp, end_stream=False)
        << SendData(tctx.client, Placeholder(bytes))
        >> http.ResponseData(1, b"y" * 30)
        << SendData(tctx.client, ff.build_data_frame(b"y" * 10).serialize())
        >> http.ResponseEndOfMessage(1)
        >> DataReceived(
            tctx.client, ff.build_goaway_frame(last_stream_id=0).serialize()
        )
        << DrainHttpConnection(tctx.client)
        >> DataReceived(tctx.client, ff.build_window_update_frame(1, 100).serialize())
        # the buffered tail, then our GOAWAY (merged into one write by the playbook)
        << SendData(tctx.client, rest)
        << CloseConnection(tctx.client)
    )
    data, end, goaway = decode_frames(rest())
    assert data.data == b"y" * 20
    assert end.data == b"" and "END_STREAM" in end.flags
    assert isinstance(goaway, hyperframe.frame.GoAwayFrame)
    assert goaway.error_code == ErrorCodes.NO_ERROR and goaway.last_stream_id == 1


@pytest.mark.parametrize("how", ["remote reset", "local reset", "error goaway"])
def test_discard_buffered_trailers(tctx, how):
    """Trailers queued behind flow-controlled data are discarded with that data."""
    tctx.options.http2_ping_keepalive = 0
    ff = FrameFactory()
    client = Http2Client(tctx)
    playbook = Playbook(client)
    req = Request.make("POST", "http://example.com/upload")
    assert (
        playbook
        << SendData(tctx.server, Placeholder(bytes))
        >> DataReceived(
            tctx.server,
            ff.build_settings_frame(
                {h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: 10}
            ).serialize(),
        )
        << SendData(tctx.server, ff.build_settings_frame({}, ack=True).serialize())
        >> http.RequestHeaders(1, req, end_stream=False)
        << SendData(tctx.server, Placeholder(bytes))
        >> http.RequestData(1, b"x" * 30)
        << SendData(tctx.server, ff.build_data_frame(b"x" * 10).serialize())
        >> http.RequestTrailers(1, Headers(example_request_trailers))
        >> http.RequestEndOfMessage(1)
    )
    assert client.h2_conn.stream_buffers and client.h2_conn.stream_trailers

    if how == "remote reset":
        assert (
            playbook
            >> DataReceived(
                tctx.server, ff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
            )
            << http.ReceiveHttp(Placeholder(http.ResponseProtocolError))
        )
    elif how == "local reset":
        assert (
            playbook
            >> http.RequestProtocolError(
                1, "cancelled", code=ErrorCode.CLIENT_DISCONNECTED
            )
            << SendData(
                tctx.server, ff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize()
            )
        )
    else:
        assert (
            playbook
            >> DataReceived(
                tctx.server,
                ff.build_goaway_frame(
                    last_stream_id=1, error_code=ErrorCodes.INTERNAL_ERROR
                ).serialize(),
            )
            << CloseConnection(tctx.server)
            << http.ReceiveHttp(Placeholder(http.ResponseProtocolError))
        )
    assert not client.h2_conn.stream_buffers
    assert not client.h2_conn.stream_trailers
