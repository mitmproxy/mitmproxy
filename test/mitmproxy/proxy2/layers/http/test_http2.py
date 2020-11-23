from typing import List, Tuple

import h2.settings
import hpack
import hyperframe.frame
import pytest
from h2.errors import ErrorCodes

from mitmproxy.http import HTTPFlow
from mitmproxy.net.http import Headers
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2.commands import CloseConnection, OpenConnection, SendData
from mitmproxy.proxy2.context import Context, Server
from mitmproxy.proxy2.events import ConnectionClosed, DataReceived
from mitmproxy.proxy2.layers import http
from mitmproxy.proxy2.layers.http._http2 import split_pseudo_headers
from test.mitmproxy.proxy2.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply

example_request_headers = (
    (b':method', b'GET'),
    (b':scheme', b'http'),
    (b':path', b'/'),
    (b':authority', b'example.com'),
)

example_response_headers = (
    (b':status', b'200'),
)


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
                << http.HttpRequestHook(flow)
                >> reply()
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
            << SendData(tctx.client,
                        cff.build_headers_frame(response_headers).serialize() +
                        cff.build_data_frame(b"", flags=["END_STREAM"]).serialize())
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
    )
    assert (
            playbook
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
