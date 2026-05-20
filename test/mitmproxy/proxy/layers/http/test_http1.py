import pytest

from mitmproxy import http
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers.http import Http1Client
from mitmproxy.proxy.layers.http import Http1Server
from mitmproxy.proxy.layers.http import ReceiveHttp
from mitmproxy.proxy.layers.http import RequestData
from mitmproxy.proxy.layers.http import RequestEndOfMessage
from mitmproxy.proxy.layers.http import RequestHeaders
from mitmproxy.proxy.layers.http import ResponseData
from mitmproxy.proxy.layers.http import ResponseEndOfMessage
from mitmproxy.proxy.layers.http import ResponseHeaders
from test.mitmproxy.proxy.tutils import Placeholder
from test.mitmproxy.proxy.tutils import Playbook


class TestServer:
    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_simple(self, tctx, pipeline):
        hdrs1 = Placeholder(RequestHeaders)
        hdrs2 = Placeholder(RequestHeaders)
        req2 = b"GET http://example.com/two HTTP/1.1\r\nHost: example.com\r\n\r\n"
        playbook = Playbook(Http1Server(tctx))
        (
            playbook
            >> DataReceived(
                tctx.client,
                b"POST http://example.com/one HTTP/1.1\r\n"
                b"Content-Length: 3\r\n"
                b"\r\n"
                b"abc" + (req2 if pipeline else b""),
            )
            << ReceiveHttp(hdrs1)
            << ReceiveHttp(RequestData(1, b"abc"))
            << ReceiveHttp(RequestEndOfMessage(1))
            >> ResponseHeaders(1, http.Response.make(200))
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
            >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, req2)
        playbook << ReceiveHttp(hdrs2)
        playbook << ReceiveHttp(RequestEndOfMessage(3))
        assert playbook

    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_connect(self, tctx, pipeline):
        playbook = Playbook(Http1Server(tctx))
        (
            playbook
            >> DataReceived(
                tctx.client,
                b"CONNECT example.com:443 HTTP/1.1\r\n"
                b"content-length: 0\r\n"
                b"\r\n" + (b"some plain tcp" if pipeline else b""),
            )
            << ReceiveHttp(Placeholder(RequestHeaders))
            # << ReceiveHttp(RequestEndOfMessage(1))
            >> ResponseHeaders(1, http.Response.make(200))
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
            >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, b"some plain tcp")
        assert playbook << ReceiveHttp(RequestData(1, b"some plain tcp"))

    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_upgrade(self, tctx, pipeline):
        playbook = Playbook(Http1Server(tctx))
        (
            playbook
            >> DataReceived(
                tctx.client,
                b"POST http://example.com/one HTTP/1.1\r\n"
                b"Connection: Upgrade\r\n"
                b"Upgrade: websocket\r\n"
                b"\r\n" + (b"some websockets" if pipeline else b""),
            )
            << ReceiveHttp(Placeholder(RequestHeaders))
            << ReceiveHttp(RequestEndOfMessage(1))
            >> ResponseHeaders(1, http.Response.make(101))
            << SendData(
                tctx.client,
                b"HTTP/1.1 101 Switching Protocols\r\ncontent-length: 0\r\n\r\n",
            )
            >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, b"some websockets")
        assert playbook << ReceiveHttp(RequestData(1, b"some websockets"))

    def test_upgrade_denied(self, tctx):
        assert (
            Playbook(Http1Server(tctx))
            >> DataReceived(
                tctx.client,
                b"GET http://example.com/ HTTP/1.1\r\n"
                b"Connection: Upgrade\r\n"
                b"Upgrade: websocket\r\n"
                b"\r\n",
            )
            << ReceiveHttp(Placeholder(RequestHeaders))
            << ReceiveHttp(RequestEndOfMessage(1))
            >> ResponseHeaders(1, http.Response.make(200))
            << SendData(tctx.client, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
            >> ResponseEndOfMessage(1)
            >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\n\r\n")
            << ReceiveHttp(Placeholder(RequestHeaders))
            << ReceiveHttp(RequestEndOfMessage(3))
        )

    def test_chunked_response_empty_data_no_terminator(self, tctx):
        """Empty ResponseData(b"") on a chunked response must NOT emit the
        chunked-encoding body-end terminator `0\r\n\r\n`.

        Before this fix, a `response.stream` callable returning `b""` (e.g. a
        rehydrator buffering events for a later flush) caused
        `b"%x\r\n%s\r\n" % (0, b"") == b"0\r\n\r\n"` to be sent, which the
        client parses as end-of-body and stops reading mid-stream.
        """
        playbook = Playbook(Http1Server(tctx))
        (
            playbook
            >> DataReceived(
                tctx.client,
                b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n",
            )
            << ReceiveHttp(Placeholder(RequestHeaders))
            << ReceiveHttp(RequestEndOfMessage(1))
            >> ResponseHeaders(
                1,
                http.Response.make(200, b"", headers={"transfer-encoding": "chunked"}),
            )
            << SendData(
                tctx.client,
                b"HTTP/1.1 200 OK\r\ntransfer-encoding: chunked\r\n\r\n",
            )
            >> ResponseData(1, b"hello")
            << SendData(tctx.client, b"5\r\nhello\r\n")
            # Empty ResponseData must produce no SendData. Playbook is strict:
            # any unexpected SendData here would fail the test.
            >> ResponseData(1, b"")
            >> ResponseData(1, b"world")
            << SendData(tctx.client, b"5\r\nworld\r\n")
            >> ResponseEndOfMessage(1)
            << SendData(tctx.client, b"0\r\n\r\n")
        )
        assert playbook


class TestClient:
    def test_chunked_request_empty_data_no_terminator(self, tctx):
        """Empty RequestData(b"") on a chunked request must NOT emit the
        chunked-encoding body-end terminator. Same bug as
        TestServer.test_chunked_response_empty_data_no_terminator, just on
        the request side.
        """
        req = http.Request.make(
            "POST",
            "http://example.com/",
            headers={"transfer-encoding": "chunked"},
        )
        playbook = Playbook(Http1Client(tctx))
        (
            playbook
            >> RequestHeaders(1, req, False)
            << SendData(
                tctx.server,
                b"POST / HTTP/1.1\r\ntransfer-encoding: chunked\r\n\r\n",
            )
            >> RequestData(1, b"hello")
            << SendData(tctx.server, b"5\r\nhello\r\n")
            # Empty RequestData → no SendData. Playbook is strict.
            >> RequestData(1, b"")
            >> RequestData(1, b"world")
            << SendData(tctx.server, b"5\r\nworld\r\n")
            >> RequestEndOfMessage(1)
            << SendData(tctx.server, b"0\r\n\r\n")
        )
        assert playbook

    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_simple(self, tctx, pipeline):
        req = http.Request.make("GET", "http://example.com/")
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        (
            playbook
            >> RequestHeaders(1, req, True)
            << SendData(tctx.server, b"GET / HTTP/1.1\r\ncontent-length: 0\r\n\r\n")
            >> RequestEndOfMessage(1)
        )
        if pipeline:
            with pytest.raises(
                AssertionError, match="assert self.stream_id == event.stream_id"
            ):
                assert playbook >> RequestHeaders(3, req, True)
            return
        assert (
            playbook
            >> DataReceived(
                tctx.server, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n"
            )
            << ReceiveHttp(resp)
            << ReceiveHttp(ResponseEndOfMessage(1))
            # no we can send the next request
            >> RequestHeaders(3, req, True)
            << SendData(tctx.server, b"GET / HTTP/1.1\r\ncontent-length: 0\r\n\r\n")
        )
        assert resp().response.status_code == 200

    def test_connect(self, tctx):
        req = http.Request.make("CONNECT", "http://example.com:443")
        req.authority = "example.com:443"
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        assert (
            playbook
            >> RequestHeaders(1, req, True)
            << SendData(
                tctx.server,
                b"CONNECT example.com:443 HTTP/1.1\r\ncontent-length: 0\r\n\r\n",
            )
            >> RequestEndOfMessage(1)
            >> DataReceived(
                tctx.server,
                b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\nsome plain tcp",
            )
            << ReceiveHttp(resp)
            # << ReceiveHttp(ResponseEndOfMessage(1))
            << ReceiveHttp(ResponseData(1, b"some plain tcp"))
            # no we can send plain data
            >> RequestData(1, b"some more tcp")
            << SendData(tctx.server, b"some more tcp")
        )

    def test_upgrade(self, tctx):
        req = http.Request.make(
            "GET",
            "http://example.com/ws",
            headers={
                "Connection": "Upgrade",
                "Upgrade": "websocket",
            },
        )
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        assert (
            playbook
            >> RequestHeaders(1, req, True)
            << SendData(
                tctx.server,
                b"GET /ws HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\ncontent-length: 0\r\n\r\n",
            )
            >> RequestEndOfMessage(1)
            >> DataReceived(
                tctx.server,
                b"HTTP/1.1 101 Switching Protocols\r\ncontent-length: 0\r\n\r\nhello",
            )
            << ReceiveHttp(resp)
            << ReceiveHttp(ResponseEndOfMessage(1))
            << ReceiveHttp(ResponseData(1, b"hello"))
            # no we can send plain data
            >> RequestData(1, b"some more websockets")
            << SendData(tctx.server, b"some more websockets")
        )

    def test_upgrade_denied(self, tctx):
        req = http.Request.make(
            "GET",
            "http://example.com/ws",
            headers={
                "Connection": "Upgrade",
                "Upgrade": "websocket",
            },
        )
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        assert (
            playbook
            >> RequestHeaders(1, req, True)
            << SendData(
                tctx.server,
                b"GET /ws HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\ncontent-length: 0\r\n\r\n",
            )
            >> RequestEndOfMessage(1)
            >> DataReceived(
                tctx.server, b"HTTP/1.1 200 Ok\r\ncontent-length: 0\r\n\r\n"
            )
            << ReceiveHttp(resp)
            << ReceiveHttp(ResponseEndOfMessage(1))
            >> RequestHeaders(3, req, True)
            << SendData(tctx.server, Placeholder(bytes))
        )
