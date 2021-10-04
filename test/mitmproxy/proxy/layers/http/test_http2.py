from typing import List, Tuple

import h2.settings
import hpack
import hyperframe.frame
import pytest
from h2.errors import ErrorCodes

from mitmproxy.connection import ConnectionState, Server
from mitmproxy.flow import Error
from mitmproxy.http import HTTPFlow, Headers, Request
from mitmproxy.net.http import status_codes
from mitmproxy.proxy.commands import CloseConnection, OpenConnection, SendData
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import ConnectionClosed, DataReceived
from mitmproxy.proxy.layers import http
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.http._http2 import Http2Client, split_pseudo_headers
from test.mitmproxy.proxy.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy.tutils import Placeholder, Playbook, reply

example_request_headers = (
    (b':method', b'GET'),
    (b':scheme', b'http'),
    (b':path', b'/'),
    (b':authority', b'example.com'),
)

example_response_headers = (
    (b':status', b'200'),
)

example_request_trailers = (
    (b'req-trailer-a', b'a'),
    (b'req-trailer-b', b'b')
)

example_response_trailers = (
    (b'resp-trailer-a', b'a'),
    (b'resp-trailer-b', b'b')
)


@pytest.fixture
def open_h2_server_conn():
    # this is a bit fake here (port 80, with alpn, but no tls - c'mon),
    # but we don't want to pollute our tests with TLS handshakes.
    s = Server(("example.com", 80))
    s.state = ConnectionState.OPEN
    s.alpn = b"h2"
    return s


def decode_frames(data: bytes) -> List[hyperframe.frame.Frame]:
    # swallow preamble
    if data.startswith(b"PRI * HTTP/2.0"):
        data = data[24:]
    frames = []
    while data:
        f, length = hyperframe.frame.Frame.parse_frame_header(data[:9])
        f.parse_body(memoryview(data[9:9 + length]))
        frames.append(f)
        data = data[9 + length:]
    return frames


def start_h2_client(tctx: Context) -> Tuple[Playbook, FrameFactory]:
    tctx.client.alpn = b"h2"
    frame_factory = FrameFactory()

    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))
    assert (
            playbook
            << SendData(tctx.client, Placeholder())  # initial settings frame
            >> DataReceived(tctx.client, frame_factory.preamble())
            >> DataReceived(tctx.client, frame_factory.build_settings_frame({}, ack=True).serialize())
    )
    return playbook, frame_factory


def make_h2(open_connection: OpenConnection) -> None:
    open_connection.connection.alpn = b"h2"


def test_simple(tctx):
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)
    initial = Placeholder(bytes)
    assert (
            playbook
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
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
        hyperframe.frame.HeadersFrame,
    ]
    sff = FrameFactory()
    assert (
            playbook
            # a conforming h2 server would send settings first, we disregard this for now.
            >> DataReceived(server, sff.build_headers_frame(example_response_headers).serialize())
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            >> DataReceived(server, sff.build_data_frame(b"Hello, World!", flags=["END_STREAM"]).serialize())
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client,
                        cff.build_headers_frame(example_response_headers).serialize() +
                        cff.build_data_frame(b"Hello, World!").serialize() +
                        cff.build_data_frame(b"", flags=["END_STREAM"]).serialize())
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
        >> DataReceived(tctx.client,
                        cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
        << http.HttpRequestHeadersHook(flow)
        >> reply()
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(tctx.server, Placeholder(bytes))
        # a conforming h2 server would send settings first, we disregard this for now.
        >> DataReceived(tctx.server, sff.build_headers_frame(example_response_headers).serialize() +
                        sff.build_data_frame(b"Hello, World!").serialize())
        << http.HttpResponseHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
    )
    if stream:
        playbook << SendData(
            tctx.client,
            cff.build_headers_frame(example_response_headers).serialize() +
            cff.build_data_frame(b"Hello, World!").serialize()
        )
    assert (
        playbook
        >> DataReceived(tctx.server, sff.build_headers_frame(example_response_trailers, flags=["END_STREAM"]).serialize())
        << http.HttpResponseHook(flow)
    )
    assert flow().response.trailers
    del flow().response.trailers["resp-trailer-a"]
    if stream:
        assert (
            playbook
            >> reply()
            << SendData(tctx.client,
                        cff.build_headers_frame(example_response_trailers[1:], flags=["END_STREAM"]).serialize())
        )
    else:
        assert (
            playbook
            >> reply()
            << SendData(tctx.client,
                        cff.build_headers_frame(example_response_headers).serialize() +
                        cff.build_data_frame(b"Hello, World!").serialize() +
                        cff.build_headers_frame(example_response_trailers[1:], flags=["END_STREAM"]).serialize()))


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
        >> DataReceived(tctx.client,
                        cff.build_headers_frame(example_request_headers).serialize() +
                        cff.build_data_frame(b"Hello, World!").serialize()
                        )
        << http.HttpRequestHeadersHook(flow)
        >> reply(side_effect=enable_streaming)
    )
    if stream:
        playbook << SendData(tctx.server, server_data1)
    assert (
        playbook
        >> DataReceived(tctx.client,
                        cff.build_headers_frame(example_request_trailers, flags=["END_STREAM"]).serialize())
        << http.HttpRequestHook(flow)
        >> reply()
        << SendData(tctx.server, server_data2)
    )
    frames = decode_frames(server_data1.setdefault(b"") + server_data2())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
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
            >> DataReceived(tctx.client, cff.build_headers_frame(example_request_headers).serialize())
            << http.HttpRequestHeadersHook(flow)
    )
    if stream and when == "request":
        assert (
                playbook
                >> reply(side_effect=enable_request_streaming)
                << OpenConnection(server)
                >> reply(None)
                << SendData(server, b"GET / HTTP/1.1\r\n"
                                    b"Host: example.com\r\n\r\n")
        )
    else:
        assert playbook >> reply()

    if when == "request":
        if "RST" in how:
            playbook >> DataReceived(tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize())
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
        assert "stream reset" in flow().error.msg or "peer closed connection" in flow().error.msg
        return

    assert (
            playbook
            >> DataReceived(tctx.client, cff.build_data_frame(b"", flags=["END_STREAM"]).serialize())
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\n"
                                b"Host: example.com\r\n\r\n")
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
        playbook >> DataReceived(tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize())
    else:
        playbook >> ConnectionClosed(tctx.client)
        playbook << CloseConnection(tctx.client)

    assert (
            playbook
            << CloseConnection(server)
            << http.HttpErrorHook(flow)
            >> reply()
    )

    if how == "RST+disconnect":
        assert (
                playbook
                >> ConnectionClosed(tctx.client)
                << CloseConnection(tctx.client)
        )

    if "RST" in how:
        assert "stream reset" in flow().error.msg
    else:
        assert "peer closed connection" in flow().error.msg


@pytest.mark.xfail(reason="inbound validation turned on to protect against request smuggling")
def test_no_normalization(tctx):
    """Test that we don't normalize headers when we just pass them through."""

    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook, cff = start_h2_client(tctx)

    request_headers = example_request_headers + (
        (b"Should-Not-Be-Capitalized! ", b" :) "),
    )
    response_headers = example_response_headers + (
        (b"Same", b"Here"),
    )

    initial = Placeholder(bytes)
    assert (
            playbook
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(request_headers, flags=["END_STREAM"]).serialize())
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
        hyperframe.frame.HeadersFrame,
    ]
    assert hpack.hpack.Decoder().decode(frames[1].data, True) == list(request_headers)

    sff = FrameFactory()
    assert (
            playbook
            >> DataReceived(server, sff.build_headers_frame(response_headers, flags=["END_STREAM"]).serialize())
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client, cff.build_headers_frame(response_headers, flags=["END_STREAM"]).serialize())
    )
    assert flow().request.headers.fields == ((b"Should-Not-Be-Capitalized! ", b" :) "),)
    assert flow().response.headers.fields == ((b"Same", b"Here"),)


@pytest.mark.parametrize("input,pseudo,headers", [
    ([(b"foo", b"bar")], {}, {"foo": "bar"}),
    ([(b":status", b"418")], {b":status": b"418"}, {}),
    ([(b":status", b"418"), (b"foo", b"bar")], {b":status": b"418"}, {"foo": "bar"}),
])
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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> DataReceived(tctx.client, cff.build_data_frame(b"unexpected data frame").serialize())
            << SendData(tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.STREAM_CLOSED).serialize())
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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')
            >> DataReceived(tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize())
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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
            << http.HttpRequestHeadersHook(flow)
            >> reply()
            << http.HttpRequestHook(flow)
            >> reply()
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')
            >> DataReceived(server, b"HTTP/1.1 204 No Content\r\n\r\n")
            << http.HttpResponseHeadersHook(flow)
            << CloseConnection(server)
            >> reply(to=-2)
            << http.HttpResponseHook(flow)
            >> DataReceived(tctx.client, cff.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize())
            >> reply(to=-2)
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

    assert (playbook
            >> DataReceived(
                tctx.client,
                cff.build_headers_frame(example_request_headers, flags=["END_STREAM"], stream_id=1).serialize() +
                cff.build_headers_frame(example_request_headers, flags=["END_STREAM"], stream_id=3).serialize())
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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"],
                                                    stream_id=1).serialize())
            << OpenConnection(server)
            >> reply(None, side_effect=make_h2)
            << SendData(server, req1_bytes)
            >> DataReceived(server,
                            sff.build_settings_frame(
                                {h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 1}).serialize())
            << SendData(server, settings_ack_bytes)
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers,
                                                    flags=["END_STREAM"],
                                                    stream_id=3).serialize())
            # Can't send it upstream yet, all streams in use!
            >> DataReceived(server, sff.build_headers_frame(example_response_headers,
                                                            flags=["END_STREAM"],
                                                            stream_id=1).serialize())
            # But now we can!
            << SendData(server, req2_bytes)
            << SendData(tctx.client, Placeholder(bytes))
            >> DataReceived(server, sff.build_headers_frame(example_response_headers,
                                                            flags=["END_STREAM"],
                                                            stream_id=3).serialize())
            << SendData(tctx.client, Placeholder(bytes))
    )
    settings, req1 = decode_frames(req1_bytes())
    settings_ack, = decode_frames(settings_ack_bytes())
    req2, = decode_frames(req2_bytes())

    assert type(settings) == hyperframe.frame.SettingsFrame
    assert type(req1) == hyperframe.frame.HeadersFrame
    assert type(settings_ack) == hyperframe.frame.SettingsFrame
    assert type(req2) == hyperframe.frame.HeadersFrame
    assert req1.stream_id == 1
    assert req2.stream_id == 3


def test_stream_concurrent_get_connection(tctx):
    """Test that an immediate second request for the same domain does not trigger a second connection attempt."""
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False

    server = Placeholder(Server)
    data = Placeholder(bytes)

    assert (playbook
            >> DataReceived(tctx.client, cff.build_headers_frame(example_request_headers, flags=["END_STREAM"],
                                                                 stream_id=1).serialize())
            << (o := OpenConnection(server))
            >> DataReceived(tctx.client, cff.build_headers_frame(example_request_headers, flags=["END_STREAM"],
                                                                 stream_id=3).serialize())
            >> reply(None, to=o, side_effect=make_h2)
            << SendData(server, data)
            )
    frames = decode_frames(data())
    assert [type(x) for x in frames] == [
        hyperframe.frame.SettingsFrame,
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

    assert (playbook
            >> DataReceived(
                tctx.client,
                cff.build_headers_frame(example_request_headers, flags=["END_STREAM"], stream_id=1).serialize() +
                cff.build_headers_frame(example_request_headers, flags=["END_STREAM"], stream_id=3).serialize())
            << req_headers_hook_1
            << http.HttpRequestHeadersHook(flow2)
            >> reply(side_effect=kill)
            << http.HttpErrorHook(flow2)
            >> reply()
            << SendData(tctx.client, cff.build_rst_stream_frame(3, error_code=ErrorCodes.INTERNAL_ERROR).serialize())
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
        hyperframe.frame.HeadersFrame,
    ]


class TestClient:
    def test_no_data_on_closed_stream(self, tctx):
        frame_factory = FrameFactory()
        req = Request.make("GET", "http://example.com/")
        resp = {
            ":status": 200
        }
        assert (
                Playbook(Http2Client(tctx))
                << SendData(tctx.server, Placeholder(bytes))  # preamble + initial settings frame
                >> DataReceived(tctx.server, frame_factory.build_settings_frame({}, ack=True).serialize())
                >> http.RequestHeaders(1, req, end_stream=True)
                << SendData(tctx.server, b"\x00\x00\x06\x01\x05\x00\x00\x00\x01\x82\x86\x84\\\x81\x07")
                >> http.RequestEndOfMessage(1)
                >> DataReceived(tctx.server, frame_factory.build_headers_frame(resp).serialize())
                << http.ReceiveHttp(Placeholder(http.ResponseHeaders))
                >> http.RequestProtocolError(1, "cancelled", code=status_codes.CLIENT_CLOSED_REQUEST)
                << SendData(tctx.server, frame_factory.build_rst_stream_frame(1, ErrorCodes.CANCEL).serialize())
                >> DataReceived(tctx.server, frame_factory.build_data_frame(b"foo").serialize())
                << SendData(tctx.server, frame_factory.build_rst_stream_frame(1, ErrorCodes.STREAM_CLOSED).serialize())
        )  # important: no ResponseData event here!


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
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(example_request_headers, flags=["END_STREAM"]).serialize())
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
        (b':method', b'POST'),
        (b':scheme', b'http'),
        (b':path', b'/'),
        (b':authority', b'example.com'),
        (b'content-length', b'3')
    )

    assert (
            playbook
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(headers).serialize())
            >> DataReceived(tctx.client,
                            cff.build_data_frame(b"abcPOST / HTTP/1.1 ...", flags=["END_STREAM"]).serialize())
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
    )
    assert b"InvalidBodyLengthError" in err()


def test_request_smuggling_te(tctx):
    playbook, cff = start_h2_client(tctx)
    playbook.hooks = False
    err = Placeholder(bytes)

    headers = (
        (b':method', b'POST'),
        (b':scheme', b'http'),
        (b':path', b'/'),
        (b':authority', b'example.com'),
        (b'transfer-encoding', b'chunked')
    )

    assert (
            playbook
            >> DataReceived(tctx.client,
                            cff.build_headers_frame(headers, flags=["END_STREAM"]).serialize())
            << SendData(tctx.client, err)
            << CloseConnection(tctx.client)
    )
    assert b"Connection-specific header field present" in err()
