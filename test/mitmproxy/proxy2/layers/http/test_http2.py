from typing import Callable, List

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


@pytest.fixture
def frame_factory() -> FrameFactory:
    return FrameFactory()


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
    frames = []
    while data:
        f, length = hyperframe.frame.Frame.parse_frame_header(data[:9])
        f.parse_body(memoryview(data[9:9 + length]))
        frames.append(f)
        data = data[9 + length:]
    return frames


def start_h2(tctx: Context, frame_factory: FrameFactory) -> Playbook:
    tctx.client.alpn = b"h2"

    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular))
    assert (
            playbook
            << SendData(tctx.client, Placeholder())  # initial settings frame
            >> DataReceived(tctx.client, frame_factory.preamble())
            >> DataReceived(tctx.client, frame_factory.build_settings_frame({}, ack=True).serialize())
    )
    return playbook


def make_h2(open_connection: OpenConnection) -> None:
    open_connection.connection.alpn = b"h2"


@pytest.mark.parametrize("stream", [True, False])
def test_http2_client_aborts(tctx, frame_factory, stream):
    """Test handling of the case where a client aborts during request transmission."""
    server = Placeholder(Server)
    flow = Placeholder(HTTPFlow)
    playbook = start_h2(tctx, frame_factory)

    def enable_streaming(flow: HTTPFlow):
        flow.request.stream = True

    assert (
            playbook
            >> DataReceived(tctx.client, frame_factory.build_headers_frame(example_request_headers).serialize())
            << http.HttpRequestHeadersHook(flow)
    )
    if stream:
        pytest.xfail("h2 client not implemented yet")
        assert (
                playbook
                >> reply(side_effect=enable_streaming)
                << OpenConnection(server)
                >> reply(None, side_effect=make_h2)
                << SendData(server, b"POST / HTTP/1.1\r\n"
                                    b"Host: example.com\r\n"
                                    b"Content-Length: 6\r\n\r\n"
                                    b"abc")
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
def test_no_normalization():
    """Test that we don't normalize headers when we just pass them through."""
    raise NotImplementedError
