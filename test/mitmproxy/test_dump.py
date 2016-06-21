import os
from six.moves import cStringIO as StringIO
from mitmproxy.exceptions import ContentViewException

import netlib.tutils

from mitmproxy import dump, flow, models, exceptions
from . import tutils, mastertest
import mock


def flowfile(path):
    f = open(path, "wb")
    fw = flow.FlowWriter(f)
    t = tutils.tflow(resp=True)
    fw.add(t)
    f.close()


def test_strfuncs():
    o = dump.Options(
        tfile = StringIO(),
        flow_detail = 0,
    )
    m = dump.DumpMaster(o, None)

    m.echo_flow(tutils.tflow())
    assert not m.options.tfile.getvalue()

    m.options.flow_detail = 4
    m.echo_flow(tutils.tflow())
    assert m.options.tfile.getvalue()

    m.options.tfile = StringIO()
    m.echo_flow(tutils.tflow(resp=True))
    assert "<<" in m.options.tfile.getvalue()

    m.options.tfile = StringIO()
    m.echo_flow(tutils.tflow(err=True))
    assert "<<" in m.options.tfile.getvalue()

    flow = tutils.tflow()
    flow.request = netlib.tutils.treq()
    flow.request.stickycookie = True
    flow.client_conn = mock.MagicMock()
    flow.client_conn.address.host = "foo"
    flow.response = netlib.tutils.tresp(content=None)
    flow.response.is_replay = True
    flow.response.status_code = 300
    m.echo_flow(flow)

    flow = tutils.tflow(resp=netlib.tutils.tresp(content="{"))
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
    m = dump.DumpMaster(o, None)
    m.echo_flow(tutils.tflow())
    assert "Content viewer failed" in m.options.tfile.getvalue()


class TestDumpMaster(mastertest.MasterTest):
    def dummy_cycle(self, master, n, content):
        mastertest.MasterTest.dummy_cycle(self, master, n, content)
        return master.options.tfile.getvalue()

    def mkmaster(self, filt, **options):
        o = dump.Options(
            filtstr=filt,
            tfile = StringIO(),
            **options
        )
        return dump.DumpMaster(o, None)

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self.dummy_cycle(self.mkmaster("~s", flow_detail=i), 1, "")
            assert "GET" in self.dummy_cycle(
                self.mkmaster("~s", flow_detail=i),
                1,
                "\x00\x00\x00"
            )
            assert "GET" in self.dummy_cycle(
                self.mkmaster("~s", flow_detail=i),
                1, "ascii"
            )

    def test_error(self):
        cs = StringIO()
        o = dump.Options(flow_detail=1, tfile=cs)
        m = dump.DumpMaster(o, None)
        f = tutils.tflow(err=True)
        m.request(f)
        m.error(f)
        assert "error" in cs.getvalue()

    def test_missing_content(self):
        cs = StringIO()
        o = dump.Options(flow_detail=3, tfile=cs)
        m = dump.DumpMaster(o, None)
        f = tutils.tflow()
        f.request.content = None
        m.request(f)
        f.response = models.HTTPResponse.wrap(netlib.tutils.tresp())
        f.response.content = None
        m.response(f)
        assert "content missing" in cs.getvalue()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay=["nonexistent"], kill=True, tfile=cs)
        tutils.raises(dump.DumpError, dump.DumpMaster, o, None)

        with tutils.tmpdir() as t:
            p = os.path.join(t, "rep")
            flowfile(p)

            o = dump.Options(server_replay=[p], kill=True, tfile=cs)
            m = dump.DumpMaster(o, None)

            self.cycle(m, "content")
            self.cycle(m, "content")

            o = dump.Options(server_replay=[p], kill=False, tfile=cs)
            m = dump.DumpMaster(o, None)
            self.cycle(m, "nonexistent")

            o = dump.Options(client_replay=[p], kill=False, tfile=cs)
            m = dump.DumpMaster(o, None)

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            flowfile(p)
            assert "GET" in self.dummy_cycle(
                self.mkmaster(None, flow_detail=1, rfile=p),
                0, "",
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
            self.mkmaster("~u foo", verbosity=1), 1, ""
        )

    def test_app(self):
        o = dump.Options(app=True)
        s = mock.MagicMock()
        m = dump.DumpMaster(o, s)
        assert len(m.apps.apps) == 1

    def test_replacements(self):
        cs = StringIO()
        o = dump.Options(replacements=[(".*", "content", "foo")], tfile=cs)
        m = dump.DumpMaster(o, None)
        f = self.cycle(m, "content")
        assert f.request.content == "foo"

    def test_setheader(self):
        cs = StringIO()
        o = dump.Options(setheaders=[(".*", "one", "two")], tfile=cs)
        m = dump.DumpMaster(o, None)
        f = self.cycle(m, "content")
        assert f.request.headers["one"] == "two"

    def test_write(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a")
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "wb"), verbosity=0), 1, ""
            )
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 1

    def test_write_append(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a.append")
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "wb"), verbosity=0),
                1, ""
            )
            self.dummy_cycle(
                self.mkmaster(None, outfile=(p, "ab"), verbosity=0),
                1, ""
            )
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 2

    def test_write_err(self):
        tutils.raises(
            dump.DumpError,
            self.mkmaster, None, outfile = ("nonexistentdir/foo", "wb")
        )

    def test_script(self):
        ret = self.dummy_cycle(
            self.mkmaster(
                None,
                scripts=[tutils.test_data.path("data/addonscripts/recorder.py")],
                verbosity=1
            ),
            1, "",
        )
        assert "clientconnect" in ret
        assert "serverconnect" in ret
        assert "request" in ret
        assert "response" in ret
        assert "clientdisconnect" in ret
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
            1, ""
        )

    def test_stickyauth(self):
        self.dummy_cycle(
            self.mkmaster(None, stickyauth = ".*"),
            1, ""
        )
