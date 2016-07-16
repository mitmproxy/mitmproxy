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

        d.configure(dump.Options(tfile = sio, flow_detail = 0))
        d.response(tutils.tflow())
        assert not sio.getvalue()

        d.configure(dump.Options(tfile = sio, flow_detail = 4))
        d.response(tutils.tflow())
        assert sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4))
        d.response(tutils.tflow(resp=True))
        assert "<<" in sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4))
        d.response(tutils.tflow(err=True))
        assert "<<" in sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio, flow_detail = 4))
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
        d.configure(dump.Options(tfile = sio, flow_detail = 4))
        flow = tutils.tflow(resp=netlib.tutils.tresp(content=b"{"))
        flow.response.headers["content-type"] = "application/json"
        flow.response.status_code = 400
        d.response(flow)
        assert sio.getvalue()

        sio = StringIO()
        d.configure(dump.Options(tfile = sio))
        flow = tutils.tflow()
        flow.request.content = None
        flow.response = models.HTTPResponse.wrap(netlib.tutils.tresp())
        flow.response.content = None
        d.response(flow)
        assert "content missing" in sio.getvalue()


class TestContentView(mastertest.MasterTest):
    @mock.patch("mitmproxy.contentviews.get_content_view")
    def test_contentview(self, get_content_view):
        se = exceptions.ContentViewException(""), ("x", iter([]))
        get_content_view.side_effect = se

        s = state.State()
        sio = StringIO()
        m = mastertest.RecordingMaster(
            dump.Options(
                flow_detail=4,
                verbosity=3,
                tfile=sio,
            ),
            None, s
        )
        d = dumper.Dumper()
        m.addons.add(d)
        self.invoke(m, "response", tutils.tflow())
        assert "Content viewer failed" in m.event_log[0][1]
