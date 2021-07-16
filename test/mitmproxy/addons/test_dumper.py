import io
import shutil
from unittest import mock

import pytest

from mitmproxy import exceptions
from mitmproxy.addons import dumper
from mitmproxy.http import Headers
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


def test_configure():
    d = dumper.Dumper()
    with taddons.context(d) as ctx:
        ctx.configure(d, dumper_filter="~b foo")
        assert d.filter

        f = tflow.tflow(resp=True)
        assert not d.match(f)
        f.response.content = b"foo"
        assert d.match(f)

        ctx.configure(d, dumper_filter=None)
        assert not d.filter
        with pytest.raises(exceptions.OptionsError):
            ctx.configure(d, dumper_filter="~~")
        assert not d.filter


def test_simple():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=0)
        d.response(tflow.tflow(resp=True))
        assert not sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=1)
        d.response(tflow.tflow(resp=True))
        assert sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=1)
        d.error(tflow.tflow(err=True))
        assert sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        d.response(tflow.tflow(resp=True))
        assert sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        d.response(tflow.tflow(resp=True))
        assert "<<" in sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        d.response(tflow.tflow(err=True))
        assert "<<" in sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        flow = tflow.tflow()
        flow.request = tutils.treq()
        flow.client_conn = mock.MagicMock()
        flow.client_conn.peername[0] = "foo"
        flow.response = tutils.tresp(content=None)
        flow.is_replay = "response"
        flow.response.status_code = 300
        d.response(flow)
        assert sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        flow = tflow.tflow(resp=tutils.tresp(content=b"{"))
        flow.response.headers["content-type"] = "application/json"
        flow.response.status_code = 400
        d.response(flow)
        assert sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=4)
        flow = tflow.tflow()
        flow.request.content = None
        flow.response = tutils.tresp(content=None)
        d.response(flow)
        assert "content missing" in sio.getvalue()
        sio.truncate(0)


def test_echo_body():
    f = tflow.tflow(client_conn=True, server_conn=True, resp=True)
    f.response.headers["content-type"] = "text/html"
    f.response.content = b"foo bar voing\n" * 100

    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=3)
        d._echo_message(f.response, f)
        t = sio.getvalue()
        assert "cut off" in t


def test_echo_trailer():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=3)
        f = tflow.tflow(client_conn=True, server_conn=True, resp=True)

        f.request.headers["content-type"] = "text/html"
        f.request.headers["transfer-encoding"] = "chunked"
        f.request.headers["trailer"] = "my-little-request-trailer"
        f.request.content = b"some request content\n" * 100
        f.request.trailers = Headers([(b"my-little-request-trailer", b"foobar-request-trailer")])

        f.response.headers["transfer-encoding"] = "chunked"
        f.response.headers["trailer"] = "my-little-response-trailer"
        f.response.content = b"some response content\n" * 100
        f.response.trailers = Headers([(b"my-little-response-trailer", b"foobar-response-trailer")])

        d.echo_flow(f)
        t = sio.getvalue()
        assert "content-type" in t
        assert "cut off" in t
        assert "some request content" in t
        assert "foobar-request-trailer" in t
        assert "some response content" in t
        assert "foobar-response-trailer" in t


def test_echo_request_line():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        f.is_replay = "request"
        d._echo_request_line(f)
        assert "[replay]" in sio.getvalue()
        sio.truncate(0)

        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        f.is_replay = None
        d._echo_request_line(f)
        assert "[replay]" not in sio.getvalue()
        sio.truncate(0)

        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        f.request.http_version = "nonstandard"
        d._echo_request_line(f)
        assert "nonstandard" in sio.getvalue()
        sio.truncate(0)

        ctx.configure(d, flow_detail=0, showhost=True)
        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        terminalWidth = max(shutil.get_terminal_size()[0] - 25, 50)
        f.request.url = "http://address:22/" + ("x" * terminalWidth) + "textToBeTruncated"
        d._echo_request_line(f)
        assert "textToBeTruncated" not in sio.getvalue()
        sio.truncate(0)


class TestContentView:
    @pytest.mark.asyncio
    async def test_contentview(self):
        with mock.patch("mitmproxy.contentviews.auto.ViewAuto.__call__") as va:
            va.side_effect = ValueError("")
            sio = io.StringIO()
            d = dumper.Dumper(sio)
            with taddons.context(d) as tctx:
                tctx.configure(d, flow_detail=4)
                d.response(tflow.tflow())
                await tctx.master.await_log("content viewer failed")


def test_tcp():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.ttcpflow()
        d.tcp_message(f)
        assert "it's me" in sio.getvalue()
        sio.truncate(0)

        f = tflow.ttcpflow(client_conn=True, err=True)
        d.tcp_error(f)
        assert "Error in TCP" in sio.getvalue()


def test_websocket():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d) as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.twebsocketflow()
        d.websocket_message(f)
        assert "it's me" in sio.getvalue()
        sio.truncate(0)

        d.websocket_end(f)
        assert "WebSocket connection closed by" in sio.getvalue()
        sio.truncate(0)

        f = tflow.twebsocketflow(err=True)
        d.websocket_end(f)
        assert "Error in WebSocket" in sio.getvalue()
        assert "(reason:" not in sio.getvalue()
        sio.truncate(0)

        f = tflow.twebsocketflow(err=True, close_reason='Some lame excuse')
        d.websocket_end(f)
        assert "Error in WebSocket" in sio.getvalue()
        assert "(reason: Some lame excuse)" in sio.getvalue()
        sio.truncate(0)

        f = tflow.twebsocketflow(close_code=4000)
        d.websocket_end(f)
        assert "UNKNOWN_ERROR=4000" in sio.getvalue()
        assert "(reason:" not in sio.getvalue()
        sio.truncate(0)

        f = tflow.twebsocketflow(close_code=4000, close_reason='I swear I had a reason')
        d.websocket_end(f)
        assert "UNKNOWN_ERROR=4000" in sio.getvalue()
        assert "(reason: I swear I had a reason)" in sio.getvalue()


def test_http2():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(d):
        f = tflow.tflow(resp=True)
        f.response.http_version = b"HTTP/2.0"
        d.response(f)
        assert "HTTP/2.0 200 OK" in sio.getvalue()
