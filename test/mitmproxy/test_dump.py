import os
from six.moves import cStringIO as StringIO
from mitmproxy.exceptions import ContentViewException
from mitmproxy.models import HTTPResponse

import netlib.tutils

from mitmproxy import dump, flow
from mitmproxy.proxy import Log
from . import tutils
import mock


def test_strfuncs():
    o = dump.Options()
    m = dump.DumpMaster(None, o)

    m.outfile = StringIO()
    m.o.flow_detail = 0
    m.echo_flow(tutils.tflow())
    assert not m.outfile.getvalue()

    m.o.flow_detail = 4
    m.echo_flow(tutils.tflow())
    assert m.outfile.getvalue()

    m.outfile = StringIO()
    m.echo_flow(tutils.tflow(resp=True))
    assert "<<" in m.outfile.getvalue()

    m.outfile = StringIO()
    m.echo_flow(tutils.tflow(err=True))
    assert "<<" in m.outfile.getvalue()

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

    o = dump.Options(flow_detail=4, verbosity=3)
    m = dump.DumpMaster(None, o, StringIO())
    m.echo_flow(tutils.tflow())
    assert "Content viewer failed" in m.outfile.getvalue()


class TestDumpMaster:

    def _cycle(self, m, content):
        f = tutils.tflow(req=netlib.tutils.treq(content=content))
        l = Log("connect")
        l.reply = mock.MagicMock()
        m.handle_log(l)
        m.handle_clientconnect(f.client_conn)
        m.handle_serverconnect(f.server_conn)
        m.handle_request(f)
        if not f.error:
            f.response = HTTPResponse.wrap(netlib.tutils.tresp(content=content))
            f = m.handle_response(f)
        m.handle_clientdisconnect(f.client_conn)
        return f

    def _dummy_cycle(self, n, filt, content, **options):
        cs = StringIO()
        o = dump.Options(filtstr=filt, **options)
        m = dump.DumpMaster(None, o, outfile=cs)
        for i in range(n):
            self._cycle(m, content)
        m.shutdown()
        return cs.getvalue()

    def _flowfile(self, path):
        f = open(path, "wb")
        fw = flow.FlowWriter(f)
        t = tutils.tflow(resp=True)
        fw.add(t)
        f.close()

    def test_error(self):
        cs = StringIO()
        o = dump.Options(flow_detail=1)
        m = dump.DumpMaster(None, o, outfile=cs)
        f = tutils.tflow(err=True)
        m.handle_request(f)
        assert m.handle_error(f)
        assert "error" in cs.getvalue()

    def test_missing_content(self):
        cs = StringIO()
        o = dump.Options(flow_detail=3)
        m = dump.DumpMaster(None, o, outfile=cs)
        f = tutils.tflow()
        f.request.content = None
        m.handle_request(f)
        f.response = HTTPResponse.wrap(netlib.tutils.tresp())
        f.response.content = None
        m.handle_response(f)
        assert "content missing" in cs.getvalue()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay=["nonexistent"], kill=True)
        tutils.raises(dump.DumpError, dump.DumpMaster, None, o, outfile=cs)

        with tutils.tmpdir() as t:
            p = os.path.join(t, "rep")
            self._flowfile(p)

            o = dump.Options(server_replay=[p], kill=True)
            m = dump.DumpMaster(None, o, outfile=cs)

            self._cycle(m, "content")
            self._cycle(m, "content")

            o = dump.Options(server_replay=[p], kill=False)
            m = dump.DumpMaster(None, o, outfile=cs)
            self._cycle(m, "nonexistent")

            o = dump.Options(client_replay=[p], kill=False)
            m = dump.DumpMaster(None, o, outfile=cs)

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            self._flowfile(p)
            assert "GET" in self._dummy_cycle(
                0,
                None,
                "",
                flow_detail=1,
                rfile=p
            )

            tutils.raises(
                dump.DumpError, self._dummy_cycle,
                0, None, "", verbosity=1, rfile="/nonexistent"
            )
            tutils.raises(
                dump.DumpError, self._dummy_cycle,
                0, None, "", verbosity=1, rfile="test_dump.py"
            )

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2

    def test_filter(self):
        assert not "GET" in self._dummy_cycle(1, "~u foo", "", verbosity=1)

    def test_app(self):
        o = dump.Options(app=True)
        s = mock.MagicMock()
        m = dump.DumpMaster(s, o)
        assert len(m.apps.apps) == 1

    def test_replacements(self):
        cs = StringIO()
        o = dump.Options(replacements=[(".*", "content", "foo")])
        m = dump.DumpMaster(None, o, outfile=cs)
        f = self._cycle(m, "content")
        assert f.request.content == "foo"

    def test_setheader(self):
        cs = StringIO()
        o = dump.Options(setheaders=[(".*", "one", "two")])
        m = dump.DumpMaster(None, o, outfile=cs)
        f = self._cycle(m, "content")
        assert f.request.headers["one"] == "two"

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self._dummy_cycle(1, "~s", "", flow_detail=i)
            assert "GET" in self._dummy_cycle(
                1,
                "~s",
                "\x00\x00\x00",
                flow_detail=i)
            assert "GET" in self._dummy_cycle(1, "~s", "ascii", flow_detail=i)

    def test_write(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a")
            self._dummy_cycle(1, None, "", outfile=(p, "wb"), verbosity=0)
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 1

    def test_write_append(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a.append")
            self._dummy_cycle(1, None, "", outfile=(p, "wb"), verbosity=0)
            self._dummy_cycle(1, None, "", outfile=(p, "ab"), verbosity=0)
            assert len(list(flow.FlowReader(open(p, "rb")).stream())) == 2

    def test_write_err(self):
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle,
            1,
            None,
            "",
            outfile = ("nonexistentdir/foo", "wb")
        )

    def test_script(self):
        ret = self._dummy_cycle(
            1, None, "",
            scripts=[tutils.test_data.path("scripts/all.py")], verbosity=1
        )
        assert "XCLIENTCONNECT" in ret
        assert "XSERVERCONNECT" in ret
        assert "XREQUEST" in ret
        assert "XRESPONSE" in ret
        assert "XCLIENTDISCONNECT" in ret
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", scripts=["nonexistent"]
        )
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", scripts=["starterr.py"]
        )

    def test_stickycookie(self):
        self._dummy_cycle(1, None, "", stickycookie = ".*")

    def test_stickyauth(self):
        self._dummy_cycle(1, None, "", stickyauth = ".*")
