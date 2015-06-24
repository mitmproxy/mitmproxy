import os
from cStringIO import StringIO
from libmproxy import dump, flow
from libmproxy.protocol import http
from libmproxy.proxy.primitives import Log
import tutils
import mock


def test_strfuncs():
    t = tutils.tresp()
    t.is_replay = True
    dump.str_response(t)

    f = tutils.tflow()
    f.client_conn = None
    f.request.stickycookie = True
    assert "stickycookie" in dump.str_request(f, False)
    assert "stickycookie" in dump.str_request(f, True)
    assert "replay" in dump.str_request(f, False)
    assert "replay" in dump.str_request(f, True)


class TestDumpMaster:
    def _cycle(self, m, content):
        f = tutils.tflow(req=tutils.treq(content))
        l = Log("connect")
        l.reply = mock.MagicMock()
        m.handle_log(l)
        m.handle_clientconnect(f.client_conn)
        m.handle_serverconnect(f.server_conn)
        m.handle_request(f)
        f.response = tutils.tresp(content)
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
        f.request.content = http.CONTENT_MISSING
        m.handle_request(f)
        f.response = tutils.tresp()
        f.response.content = http.CONTENT_MISSING
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
        assert f.request.headers["one"] == ["two"]

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
