import io
from mitmproxy.test import tflow

from .. import tutils, mastertest

from mitmproxy.addons import dumper
from mitmproxy import exceptions
from mitmproxy.tools import dump
from mitmproxy import http
from mitmproxy import proxy
import mitmproxy.test.tutils
import mock


class TestDumper(mastertest.MasterTest):
    def test_simple(self):
        d = dumper.Dumper()
        sio = io.StringIO()

        updated = {"tfile", "flow_detail"}
        d.configure(dump.Options(tfile = sio, flow_detail = 0), updated)
        d.response(tflow.tflow())
        assert not sio.getvalue()

        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tflow.tflow())
        assert sio.getvalue()

        sio = io.StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tflow.tflow(resp=True))
        assert "<<" in sio.getvalue()

        sio = io.StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tflow.tflow(err=True))
        assert "<<" in sio.getvalue()

        sio = io.StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
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
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        flow = tflow.tflow(resp=mitmproxy.test.tutils.tresp(content=b"{"))
        flow.response.headers["content-type"] = "application/json"
        flow.response.status_code = 400
        d.response(flow)
        assert sio.getvalue()

        sio = io.StringIO()
        d.configure(dump.Options(tfile = sio), updated)
        flow = tflow.tflow()
        flow.request.content = None
        flow.response = http.HTTPResponse.wrap(mitmproxy.test.tutils.tresp())
        flow.response.content = None
        d.response(flow)
        assert "content missing" in sio.getvalue()


class TestContentView(mastertest.MasterTest):
    @mock.patch("mitmproxy.contentviews.ViewAuto.__call__")
    def test_contentview(self, view_auto):
        view_auto.side_effect = exceptions.ContentViewException("")

        sio = io.StringIO()
        o = dump.Options(
            flow_detail=4,
            verbosity=3,
            tfile=sio,
        )
        m = mastertest.RecordingMaster(o, proxy.DummyServer())
        d = dumper.Dumper()
        m.addons.add(d)
        m.response(tflow.tflow())
        assert "Content viewer failed" in m.event_log[0][1]
