from .. import tutils, mastertest
from six.moves import cStringIO as StringIO

from mitmproxy.builtins import dumper
from mitmproxy.flow import state
from mitmproxy import exceptions
from mitmproxy import dump
from mitmproxy import models
import netlib.tutils
import mock


class TestDumper(mastertest.MasterTest):
    def test_simple(self):
        d = dumper.Dumper()
        sio = StringIO()

        updated = {"tfile", "flow_detail"}
        d.configure(dump.Options(tfile = sio, flow_detail = 0), updated)
        d.response(tutils.tflow())
        assert not sio.getvalue()

        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tutils.tflow())
        assert sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tutils.tflow(resp=True))
        assert "<<" in sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        d.response(tutils.tflow(err=True))
        assert "<<" in sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        flow = tutils.tflow()
        flow.request = netlib.tutils.treq()
        flow.request.stickycookie = True
        flow.client_conn = mock.MagicMock()
        flow.client_conn.address.host = "foo"
        flow.response = netlib.tutils.tresp(content=None)
        flow.response.is_replay = True
        flow.response.status_code = 300
        d.response(flow)
        assert sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4), updated)
        flow = tutils.tflow(resp=netlib.tutils.tresp(content=b"{"))
        flow.response.headers["content-type"] = "application/json"
        flow.response.status_code = 400
        d.response(flow)
        assert sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio), updated)
        flow = tutils.tflow()
        flow.request.content = None
        flow.response = models.HTTPResponse.wrap(netlib.tutils.tresp())
        flow.response.content = None
        d.response(flow)
        assert "content missing" in sio.getvalue()


class TestContentView(mastertest.MasterTest):
    @mock.patch("mitmproxy.contentviews.ViewAuto.__call__")
    def test_contentview(self, view_auto):
        view_auto.side_effect = exceptions.ContentViewException("")

        s = state.State()
        sio = StringIO()
        o = dump.Options(
            flow_detail=4,
            verbosity=3,
            tfile=sio,
        )
        m = mastertest.RecordingMaster(o, None, s)
        d = dumper.Dumper()
        m.addons.add(o, d)
        m.response(tutils.tflow())
        assert "Content viewer failed" in m.event_log[0][1]
