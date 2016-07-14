import os
from six.moves import cStringIO as StringIO
from mitmproxy.exceptions import ContentViewException

import netlib.tutils

from mitmproxy import dump, flow, models, exceptions
from . import tutils, mastertest
import mock


def test_strfuncs():
    o = dump.Options(
        tfile = StringIO(),
        flow_detail = 0,
    )
    m = dump.DumpMaster(None, o)

    m.o.flow_detail = 0
    m.echo_flow(tutils.tflow())
    assert not o.tfile.getvalue()

    m.o.flow_detail = 4
    m.echo_flow(tutils.tflow())
    assert o.tfile.getvalue()

    o.tfile = StringIO()
    m.echo_flow(tutils.tflow(resp=True))
    assert "<<" in o.tfile.getvalue()

    o.tfile = StringIO()
    m.echo_flow(tutils.tflow(err=True))
    assert "<<" in o.tfile.getvalue()

    flow = tutils.tflow()
    flow.request = netlib.tutils.treq()
    flow.request.stickycookie = True
    flow.client_conn = mock.MagicMock()
    flow.client_conn.address.host = "foo"
    flow.response = netlib.tutils.tresp(content=None)
    flow.response.is_replay = True
    flow.response.status_code = 300
    m.echo_flow(flow)

    flow = tutils.tflow(resp=netlib.tutils.tresp(content=b"{"))
    flow.response.headers["content-type"] = "application/json"
    flow.response.status_code = 400
    m.echo_flow(flow)


@mock.patch("mitmproxy.contentviews.get_content_view")
def test_contentview(get_content_view):
    get_content_view.side_effect = ContentViewException(""), ("x", iter([]))

    o = dump.Options(
        flow_detail=4,
        verbosity=3,
        tfile=StringIO(),
    )
    m = dump.DumpMaster(None, o)
    m.echo_flow(tutils.tflow())
    assert "Content viewer failed" in m.options.tfile.getvalue()


class TestDumpMaster(mastertest.MasterTest):
    def dummy_cycle(self, master, n, content):
        mastertest.MasterTest.dummy_cycle(self, master, n, content)
        return master.options.tfile.getvalue()

    def mkmaster(self, filt, **options):
        if "verbosity" not in options:
            options["verbosity"] = 0
        if "flow_detail" not in options:
            options["flow_detail"] = 0
        o = dump.Options(
            filtstr=filt,
            tfile=StringIO(),
            **options
        )
        return dump.DumpMaster(None, o)

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self.dummy_cycle(
                self.mkmaster("~s", flow_detail=i),
                1,
                b""
            )
            assert "GET" in self.dummy_cycle(
                self.mkmaster("~s", flow_detail=i),
                1,
                b"\x00\x00\x00"
            )
            assert "GET" in self.dummy_cycle(
                self.mkmaster("~s", flow_detail=i),
                1,
                b"ascii"
            )

    def test_error(self):
        o = dump.Options(
            tfile=StringIO(),
            flow_detail=1
        )
        m = dump.DumpMaster(None, o)
        f = tutils.tflow(err=True)
        m.request(f)
        assert m.error(f)
        assert "error" in o.tfile.getvalue()

    def test_missing_content(self):
        o = dump.Options(
            flow_detail=3,
            tfile=StringIO(),
        )
        m = dump.DumpMaster(None, o)
        f = tutils.tflow()
        f.request.content = None
        m.request(f)
        f.response = models.HTTPResponse.wrap(netlib.tutils.tresp())
        f.response.content = None
        m.response(f)
        assert "content missing" in o.tfile.getvalue()

    def test_replay(self):
        o = dump.Options(server_replay=["nonexistent"], kill=True)
        tutils.raises(dump.DumpError, dump.DumpMaster, None, o)

        with tutils.tmpdir() as t:
            p = os.path.join(t, "rep")
            self.flowfile(p)

            o = dump.Options(server_replay=[p], kill=True)
            o.verbosity = 0
            o.flow_detail = 0
            m = dump.DumpMaster(None, o)

            self.cycle(m, b"content")
            self.cycle(m, b"content")

            o = dump.Options(server_replay=[p], kill=False)
            o.verbosity = 0
            o.flow_detail = 0
            m = dump.DumpMaster(None, o)
            self.cycle(m, b"nonexistent")

            o = dump.Options(client_replay=[p], kill=False)
            o.verbosity = 0
            o.flow_detail = 0
            m = dump.DumpMaster(None, o)

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            self.flowfile(p)
            assert "GET" in self.dummy_cycle(
                self.mkmaster(None, flow_detail=1, rfile=p),
                0, b"",
            )

            tutils.raises(
                dump.DumpError,
                self.mkmaster, None, verbosity=1, rfile="/nonexistent"
            )
            tutils.raises(
                dump.DumpError,
                self.mkmaster, None, verbosity=1, rfile="test_dump.py"
            )

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2

    def test_filter(self):
        assert "GET" not in self.dummy_cycle(
            self.mkmaster("~u foo", verbosity=1), 1, b""
        )

    def test_app(self):
        o = dump.Options(app=True)
        s = mock.MagicMock()
        m = dump.DumpMaster(s, o)
        assert len(m.apps.apps) == 1

    def test_replacements(self):
        o = dump.Options(
            replacements=[(".*", "content", "foo")],
            tfile = StringIO(),
        )
        o.verbosity = 0
        o.flow_detail = 0
        m = dump.DumpMaster(None, o)
        f = self.cycle(m, b"content")
        assert f.request.content == b"foo"

    def test_setheader(self):
        o = dump.Options(
            setheaders=[(".*", "one", "two")],
            tfile=StringIO()
        )
        o.verbosity = 0
        o.flow_detail = 0
        m = dump.DumpMaster(None, o)
        f = self.cycle(m, b"content")
        assert f.request.headers["one"] == "two"

    def test_write(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a")
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "wb"), verbosity=0), 1, b""
            )
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 1

    def test_write_append(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a.append")
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "wb"), verbosity=0),
                1, b""
            )
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "ab"), verbosity=0),
                1, b""
            )
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 2

    def test_write_err(self):
        tutils.raises(
            exceptions.OptionsError,
            self.mkmaster, None, outfile = ("nonexistentdir/foo", "wb")
        )

    def test_script(self):
        ret = self.dummy_cycle(
            self.mkmaster(
                None,
                scripts=[tutils.test_data.path("data/scripts/all.py")], verbosity=1
            ),
            1, b"",
        )
        assert "XCLIENTCONNECT" in ret
        assert "XSERVERCONNECT" in ret
        assert "XREQUEST" in ret
        assert "XRESPONSE" in ret
        assert "XCLIENTDISCONNECT" in ret
        tutils.raises(
            exceptions.AddonError,
            self.mkmaster,
            None, scripts=["nonexistent"]
        )
        tutils.raises(
            exceptions.AddonError,
            self.mkmaster,
            None, scripts=["starterr.py"]
        )

    def test_stickycookie(self):
        self.dummy_cycle(
            self.mkmaster(None, stickycookie = ".*"),
            1, b""
        )

    def test_stickyauth(self):
        self.dummy_cycle(
            self.mkmaster(None, stickyauth = ".*"),
            1, b""
        )
