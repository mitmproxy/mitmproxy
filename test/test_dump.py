import os
from cStringIO import StringIO
from libmproxy import dump, flow, proxy
import tutils
import mock

def test_strfuncs():
    t = tutils.tresp()
    t._set_replay()
    dump.str_response(t)

    t = tutils.treq()
    t.client_conn = None
    t.stickycookie = True
    assert "stickycookie" in dump.str_request(t, False)
    assert "stickycookie" in dump.str_request(t, True)
    assert "replay" in dump.str_request(t, False)
    assert "replay" in dump.str_request(t, True)


class TestDumpMaster:
    def _cycle(self, m, content):
        req = tutils.treq()
        req.content = content
        l = proxy.Log("connect")
        l.reply = mock.MagicMock()
        m.handle_log(l)
        cc = req.client_conn
        cc.connection_error = "error"
        resp = tutils.tresp(req)
        resp.content = content
        m.handle_clientconnect(cc)
        m.handle_request(req)
        f = m.handle_response(resp)
        cd = flow.ClientDisconnect(cc)
        cd.reply = mock.MagicMock()
        m.handle_clientdisconnect(cd)
        return f

    def _dummy_cycle(self, n, filt, content, **options):
        cs = StringIO()
        o = dump.Options(**options)
        m = dump.DumpMaster(None, o, filt, outfile=cs)
        for i in range(n):
            self._cycle(m, content)
        return cs.getvalue()

    def _flowfile(self, path):
        f = open(path, "wb")
        fw = flow.FlowWriter(f)
        t = tutils.tflow_full()
        t.response = tutils.tresp(t.request)
        fw.add(t)
        f.close()

    def test_error(self):
        cs = StringIO()
        o = dump.Options(verbosity=1)
        m = dump.DumpMaster(None, o, None, outfile=cs)
        f = tutils.tflow_err()
        m.handle_request(f.request)
        assert m.handle_error(f.error)
        assert "error" in cs.getvalue()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay="nonexistent", kill=True)
        tutils.raises(dump.DumpError, dump.DumpMaster, None, o, None, outfile=cs)

        with tutils.tmpdir() as t:
            p = os.path.join(t, "rep")
            self._flowfile(p)

            o = dump.Options(server_replay=p, kill=True)
            m = dump.DumpMaster(None, o, None, outfile=cs)

            self._cycle(m, "content")
            self._cycle(m, "content")

            o = dump.Options(server_replay=p, kill=False)
            m = dump.DumpMaster(None, o, None, outfile=cs)
            self._cycle(m, "nonexistent")

            o = dump.Options(client_replay=p, kill=False)
            m = dump.DumpMaster(None, o, None, outfile=cs)

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            self._flowfile(p)
            assert "GET" in self._dummy_cycle(0, None, "", verbosity=1, rfile=p)

            tutils.raises(
                dump.DumpError, self._dummy_cycle,
                0, None, "", verbosity=1, rfile="/nonexistent"
            )

            # We now just ignore errors
            self._dummy_cycle(0, None, "", verbosity=1, rfile=tutils.test_data.path("test_dump.py"))

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2

    def test_filter(self):
        assert not "GET" in self._dummy_cycle(1, "~u foo", "", verbosity=1)

    def test_app(self):
        o = dump.Options(app=True)
        s = mock.MagicMock()
        m = dump.DumpMaster(s, o, None)
        assert s.apps.add.call_count == 2

    def test_replacements(self):
        o = dump.Options(replacements=[(".*", "content", "foo")])
        m = dump.DumpMaster(None, o, None)
        f = self._cycle(m, "content")
        assert f.request.content == "foo"

    def test_setheader(self):
        o = dump.Options(setheaders=[(".*", "one", "two")])
        m = dump.DumpMaster(None, o, None)
        f = self._cycle(m, "content")
        assert f.request.headers["one"] == ["two"]

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self._dummy_cycle(1, "~s", "", verbosity=i, eventlog=True)
            assert "GET" in self._dummy_cycle(1, "~s", "\x00\x00\x00", verbosity=i)
            assert "GET" in self._dummy_cycle(1, "~s", "ascii", verbosity=i)

    def test_write(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a")
            self._dummy_cycle(1, None, "", wfile=p, verbosity=0)
            assert len(list(flow.FlowReader(open(p,"rb")).stream())) == 1

    def test_write_err(self):
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle,
            1,
            None,
            "",
            wfile = "nonexistentdir/foo"
        )

    def test_script(self):
        ret = self._dummy_cycle(
            1, None, "",
            script=tutils.test_data.path("scripts/all.py"), verbosity=0, eventlog=True
        )
        assert "XCLIENTCONNECT" in ret
        assert "XREQUEST" in ret
        assert "XRESPONSE" in ret
        assert "XCLIENTDISCONNECT" in ret
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", script="nonexistent"
        )
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", script="starterr.py"
        )

    def test_stickycookie(self):
        self._dummy_cycle(1, None, "", stickycookie = ".*")

    def test_stickyauth(self):
        self._dummy_cycle(1, None, "", stickyauth = ".*")

