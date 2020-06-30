from typing import Callable, List, Tuple

import hpack
import hyperframe.frame
import pytest

from mitmproxy.http import HTTPFlow
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2.commands import CloseConnection, OpenConnection, SendData
from mitmproxy.proxy2.context import Context, Server
from mitmproxy.proxy2.events import ConnectionClosed, DataReceived
from mitmproxy.proxy2.layers import http
from test.mitmproxy.proxy2.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply

example_request_headers = (
    (b':authority', b'example.com'),
    (b':path', b'/'),
    (b':scheme', b'https'),
    (b':method', b'GET'),
)

example_response_headers = (
    (b':status', b'200'),
    (b'content-length', b'12'),
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


@pytest.mark.parametrize("stream", [True, False])
def test_http2_client_aborts(tctx, stream):
    """Test handling of the case where a client aborts during request transmission."""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook, cff = start_h2_client(tctx)

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = True

    assert (
            playbook
            >> DataReceived(tctx.client, cff.build_headers_frame(example_request_headers).serialize())
            << http.HttpRequestHeadersHook(flow)
    )
    if stream:
        assert (
                playbook
                >> reply(side_effect=enable_streaming)
                << OpenConnection(server)
                >> reply(None)
                << SendData(server, b"GET / HTTP/1.1\r\n"
                                    b"Host: example.com\r\n\r\n")
        )
    else:
        assert playbook >> reply()
    assert (
            playbook
            >> ConnectionClosed(tctx.client)
            << CloseConnection(tctx.client)
            << http.HttpErrorHook(flow)
            >> reply()

    )

    assert "peer closed connection" in flow().error.msg


@pytest.mark.xfail
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
        hyperframe.frame.DataFrame
    ]
    assert hpack.hpack.Decoder().decode(frames[1].data, True) == list(request_headers)

    sff = FrameFactory()
    assert (
            playbook
            << SendData(server, sff.build_headers_frame(request_headers, flags=["END_STREAM"]).serialize())
            >> DataReceived(server, sff.build_headers_frame(response_headers, flags=["END_STREAM"]).serialize())
            << http.HttpResponseHeadersHook(flow)
            >> reply()
            << http.HttpResponseHook(flow)
            >> reply()
            << SendData(tctx.client, cff.build_headers_frame(response_headers, flags=["END_STREAM"]).serialize())
    )
    assert flow().request.headers.fields == request_headers
    assert flow().response.headers.fields == response_headers


def start_h2_server(playbook: Playbook) -> FrameFactory:
    frame_factory = FrameFactory()
    server = Placeholder(Server)
    assert (
            playbook
            >> reply(None, side_effect=make_h2)
            << SendData(server, Placeholder())
    )
    playbook >> DataReceived(server, frame_factory.build_settings_frame({}, ack=True))
    return frame_factory
