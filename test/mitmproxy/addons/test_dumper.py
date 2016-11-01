import io
from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import dumper
from mitmproxy import exceptions
from mitmproxy.tools import dump
from mitmproxy import http
import mitmproxy.test.tutils
import mock


def test_simple():
    d = dumper.Dumper()
    with taddons.context(options=dump.Options()) as ctx:
        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 0)
        d.response(tflow.tflow())
        assert not sio.getvalue()

        ctx.configure(d, tfile = sio, flow_detail = 4)
        d.response(tflow.tflow())
        assert sio.getvalue()

        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 4)
        d.response(tflow.tflow(resp=True))
        assert "<<" in sio.getvalue()

        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 4)
        d.response(tflow.tflow(err=True))
        assert "<<" in sio.getvalue()

        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 4)
        flow = tflow.tflow()
        flow.request = mitmproxy.test.tutils.treq()
        flow.request.stickycookie = True
        flow.client_conn = mock.MagicMock()
        flow.client_conn.address.host = "foo"
        flow.response = mitmproxy.test.tutils.tresp(content=None)
        flow.response.is_replay = True
        flow.response.status_code = 300
        d.response(flow)
        assert sio.getvalue()

        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 4)
        flow = tflow.tflow(resp=mitmproxy.test.tutils.tresp(content=b"{"))
        flow.response.headers["content-type"] = "application/json"
        flow.response.status_code = 400
        d.response(flow)
        assert sio.getvalue()

        sio = io.StringIO()
        ctx.configure(d, tfile = sio, flow_detail = 4)
        flow = tflow.tflow()
        flow.request.content = None
        flow.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        flow.response.content = None
        d.response(flow)
        assert "content missing" in sio.getvalue()


class TestContentView:
    @mock.patch("mitmproxy.contentviews.ViewAuto.__call__")
    def test_contentview(self, view_auto):
        view_auto.side_effect = exceptions.ContentViewException("")
        d = dumper.Dumper()
        with taddons.context(options=dump.Options()) as ctx:
            sio = io.StringIO()
            ctx.configure(d, flow_detail=4, verbosity=3, tfile=sio)
            d.response(tflow.tflow())
            assert "Content viewer failed" in ctx.master.event_log[0][1]
