import io
from mitmproxy.test import tflow
from mitmproxy.test import taddons
from mitmproxy.test import tutils

from mitmproxy.addons import dumper
from mitmproxy import exceptions
from mitmproxy.tools import dump
from mitmproxy import http
import shutil
import mock


def test_configure():
    d = dumper.Dumper()
    with taddons.context(options=dump.Options()) as ctx:
        ctx.configure(d, filtstr="~b foo")
        assert d.filter

        f = tflow.tflow(resp=True)
        assert not d.match(f)
        f.response.content = b"foo"
        assert d.match(f)

        ctx.configure(d, filtstr=None)
        assert not d.filter
        tutils.raises(exceptions.OptionsError, ctx.configure, d, filtstr="~~")
        assert not d.filter


def test_simple():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(options=dump.Options()) as ctx:
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
        flow.request.stickycookie = True
        flow.client_conn = mock.MagicMock()
        flow.client_conn.address.host = "foo"
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
    with taddons.context(options=dump.Options()) as ctx:
        ctx.configure(d, flow_detail=3)
        d._echo_message(f.response)
        t = sio.getvalue()
        assert "cut off" in t


def test_echo_request_line():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(options=dump.Options()) as ctx:
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
        with taddons.context(options=dump.Options()) as ctx:
            ctx.configure(d, flow_detail=4, verbosity=3)
            d.response(tflow.tflow())
            assert "Content viewer failed" in ctx.master.event_log[0][1]


def test_tcp():
    sio = io.StringIO()
    d = dumper.Dumper(sio)
    with taddons.context(options=dump.Options()) as ctx:
        ctx.configure(d, flow_detail=3, showhost=True)
        f = tflow.ttcpflow(client_conn=True, server_conn=True)
        d.tcp_message(f)
        assert "it's me" in sio.getvalue()
        sio.truncate(0)

        f = tflow.ttcpflow(client_conn=True, err=True)
        d.tcp_error(f)
        assert "Error in TCP" in sio.getvalue()
