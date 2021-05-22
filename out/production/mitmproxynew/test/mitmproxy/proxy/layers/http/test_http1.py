import pytest

from mitmproxy import http
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers.http import Http1Server, ReceiveHttp, RequestHeaders, RequestEndOfMessage, \
    ResponseHeaders, ResponseEndOfMessage, RequestData, Http1Client, ResponseData
from test.mitmproxy.proxy.tutils import Placeholder, Playbook


class TestServer:
    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_simple(self, tctx, pipeline):
        hdrs1 = Placeholder(RequestHeaders)
        hdrs2 = Placeholder(RequestHeaders)
        req2 = (
            b"GET http://example.com/two HTTP/1.1\r\n"
            b"Host: example.com\r\n"
            b"\r\n"
        )
        playbook = Playbook(Http1Server(tctx))
        (
                playbook
                >> DataReceived(tctx.client,
                                b"POST http://example.com/one HTTP/1.1\r\n"
                                b"Content-Length: 3\r\n"
                                b"\r\n"
                                b"abc"
                                + (req2 if pipeline else b""))
                << ReceiveHttp(hdrs1)
                << ReceiveHttp(RequestData(1, b"abc"))
                << ReceiveHttp(RequestEndOfMessage(1))
                >> ResponseHeaders(1, http.Response.make(200))
                << SendData(tctx.client, b'HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n')
                >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, req2)
        assert (
                playbook
                << ReceiveHttp(hdrs2)
                << ReceiveHttp(RequestEndOfMessage(3))
        )

    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_connect(self, tctx, pipeline):
        playbook = Playbook(Http1Server(tctx))
        (
                playbook
                >> DataReceived(tctx.client,
                                b"CONNECT example.com:443 HTTP/1.1\r\n"
                                b"content-length: 0\r\n"
                                b"\r\n"
                                + (b"some plain tcp" if pipeline else b""))
                << ReceiveHttp(Placeholder(RequestHeaders))
                # << ReceiveHttp(RequestEndOfMessage(1))
                >> ResponseHeaders(1, http.Response.make(200))
                << SendData(tctx.client, b'HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n')
                >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, b"some plain tcp")
        assert (playbook
                << ReceiveHttp(RequestData(1, b"some plain tcp"))
                )

    @pytest.mark.parametrize("pipeline", ["pipeline", None])
    def test_upgrade(self, tctx, pipeline):
        playbook = Playbook(Http1Server(tctx))
        (
                playbook
                >> DataReceived(tctx.client,
                                b"POST http://example.com/one HTTP/1.1\r\n"
                                b"Connection: Upgrade\r\n"
                                b"Upgrade: websocket\r\n"
                                b"\r\n"
                                + (b"some websockets" if pipeline else b""))
                << ReceiveHttp(Placeholder(RequestHeaders))
                << ReceiveHttp(RequestEndOfMessage(1))
                >> ResponseHeaders(1, http.Response.make(101))
                << SendData(tctx.client, b'HTTP/1.1 101 Switching Protocols\r\ncontent-length: 0\r\n\r\n')
                >> ResponseEndOfMessage(1)
        )
        if not pipeline:
            playbook >> DataReceived(tctx.client, b"some websockets")
        assert (playbook
                << ReceiveHttp(RequestData(1, b"some websockets"))
                )

    def test_upgrade_denied(self, tctx):
        assert (
                Playbook(Http1Server(tctx))
                >> DataReceived(tctx.client,
                                b"GET http://example.com/ HTTP/1.1\r\n"
                                b"Connection: Upgrade\r\n"
                                b"Upgrade: websocket\r\n"
                                b"\r\n")
                << ReceiveHttp(Placeholder(RequestHeaders))
                << ReceiveHttp(RequestEndOfMessage(1))
                >> ResponseHeaders(1, http.Response.make(200))
                << SendData(tctx.client, b'HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n')
                >> ResponseEndOfMessage(1)
                >> DataReceived(tctx.client, b"GET / HTTP/1.1\r\n\r\n")
                << ReceiveHttp(Placeholder(RequestHeaders))
                << ReceiveHttp(RequestEndOfMessage(3))
        )


class TestClient:
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
            with pytest.raises(AssertionError, match="assert self.stream_id == event.stream_id"):
                assert (playbook
                        >> RequestHeaders(3, req, True)
                        )
            return
        assert (
                playbook
                >> DataReceived(tctx.server, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
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
                << SendData(tctx.server, b"CONNECT example.com:443 HTTP/1.1\r\ncontent-length: 0\r\n\r\n")
                >> RequestEndOfMessage(1)
                >> DataReceived(tctx.server, b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\nsome plain tcp")
                << ReceiveHttp(resp)
                # << ReceiveHttp(ResponseEndOfMessage(1))
                << ReceiveHttp(ResponseData(1, b"some plain tcp"))
                # no we can send plain data
                >> RequestData(1, b"some more tcp")
                << SendData(tctx.server, b"some more tcp")
        )

    def test_upgrade(self, tctx):
        req = http.Request.make("GET", "http://example.com/ws", headers={
            "Connection": "Upgrade",
            "Upgrade": "websocket",
        })
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        assert (
                playbook
                >> RequestHeaders(1, req, True)
                << SendData(tctx.server,
                            b"GET /ws HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\ncontent-length: 0\r\n\r\n")
                >> RequestEndOfMessage(1)
                >> DataReceived(tctx.server, b"HTTP/1.1 101 Switching Protocols\r\ncontent-length: 0\r\n\r\nhello")
                << ReceiveHttp(resp)
                << ReceiveHttp(ResponseEndOfMessage(1))
                << ReceiveHttp(ResponseData(1, b"hello"))
                # no we can send plain data
                >> RequestData(1, b"some more websockets")
                << SendData(tctx.server, b"some more websockets")
        )

    def test_upgrade_denied(self, tctx):
        req = http.Request.make("GET", "http://example.com/ws", headers={
            "Connection": "Upgrade",
            "Upgrade": "websocket",
        })
        resp = Placeholder(ResponseHeaders)

        playbook = Playbook(Http1Client(tctx))
        assert (
                playbook
                >> RequestHeaders(1, req, True)
                << SendData(tctx.server,
                            b"GET /ws HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\ncontent-length: 0\r\n\r\n")
                >> RequestEndOfMessage(1)
                >> DataReceived(tctx.server, b"HTTP/1.1 200 Ok\r\ncontent-length: 0\r\n\r\n")
                << ReceiveHttp(resp)
                << ReceiveHttp(ResponseEndOfMessage(1))
                >> RequestHeaders(3, req, True)
                << SendData(tctx.server, Placeholder(bytes))
        )
