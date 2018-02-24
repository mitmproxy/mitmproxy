import io
import shutil
import pytest
from unittest import mock

from mitmproxy.test import tflow
from mitmproxy.test import taddons
from mitmproxy.test import tutils

from mitmproxy.addons import dumper
from mitmproxy import exceptions
from mitmproxy import http


def test_configure():
    d = dumper.Dumper()
    with taddons.context() as ctx:
        ctx.configure(d, view_filter="~b foo")
        assert d.filter

        f = tflow.tflow(resp=True)
        assert not d.match(f)
        f.response.content = b"foo"
        assert d.match(f)

        ctx.configure(d, view_filter=None)
        assert not d.filter
        with pytest.raises(exceptions.OptionsError):
            ctx.configure(d, view_filter="~~")
        assert not d.filter


def test_simple():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context() as ctx:
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
        flow.client_conn.address[0] = "foo"
        flow.response = tutils.tresp(content=None)
        flow.response.is_replay = True
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
        flow.response = http.HTTPResponse.wrap(tutils.tresp())
        flow.response.content = None
        d.response(flow)
        assert "content missing" in sio.getvalue()
        sio.truncate(0)


def test_echo_body():
    f = tflow.tflow(client_conn=True, server_conn=True, resp=True)
    f.response.headers["content-type"] = "text/html"
    f.response.content = b"foo bar voing\n" * 100

    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context() as ctx:
        ctx.configure(d, flow_detail=3)
        d._echo_message(f.response)
        t = sio.getvalue()
        assert "cut off" in t


def test_echo_request_line():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context() as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        f.request.is_replay = True
        d._echo_request_line(f)
        assert "[replay]" in sio.getvalue()
        sio.truncate(0)

        f = tflow.tflow(client_conn=None, server_conn=True, resp=True)
        f.request.is_replay = False
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
    @mock.patch("mitmproxy.contentviews.auto.ViewAuto.__call__")
    def test_contentview(self, view_auto):
        view_auto.side_effect = exceptions.ContentViewException("")
        sio = io.StringIO()
        d = dumper.Dumper(sio)
        with taddons.context() as ctx:
            ctx.configure(d, flow_detail=4, verbosity='debug')
            d.response(tflow.tflow())
            assert ctx.master.has_log("content viewer failed")


def test_tcp():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context() as ctx:
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
    with taddons.context() as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.twebsocketflow()
        d.websocket_message(f)
        assert "it's me" in sio.getvalue()
        sio.truncate(0)

        d.websocket_end(f)
        assert "WebSocket connection closed by" in sio.getvalue()

        f = tflow.twebsocketflow(client_conn=True, err=True)
        d.websocket_error(f)
        assert "Error in WebSocket" in sio.getvalue()
