import os
from cStringIO import StringIO
import libpry
from libmproxy import dump, flow
import tutils

class uStrFuncs(libpry.AutoTree):
    def test_all(self):
        t = tutils.tresp()
        t._set_replay()
        dump.str_response(t)

        t = tutils.treq()
        t.client_conn = None
        t.stickycookie = True
        assert "stickycookie" in dump.str_request(t)
        assert "replay" in dump.str_request(t)


class uDumpMaster(libpry.AutoTree):
    def _cycle(self, m, content):
        req = tutils.treq()
        req.content = content
        cc = req.client_conn
        cc.connection_error = "error"
        resp = tutils.tresp(req)
        resp.content = content
        m.handle_clientconnect(cc)
        m.handle_request(req)
        m.handle_response(resp)
        m.handle_clientdisconnect(flow.ClientDisconnect(cc))

    def _dummy_cycle(self, n, filt, content, **options):
        cs = StringIO()
        o = dump.Options(**options)
        m = dump.DumpMaster(None, o, filt, outfile=cs)
        for i in range(n):
            self._cycle(m, content)
        return cs.getvalue()

    def _flowfile(self, path):
        f = open(path, "w")
        fw = flow.FlowWriter(f)
        t = tutils.tflow_full()
        t.response = tutils.tresp(t.request)
        fw.add(t)
        f.close()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay="nonexistent", kill=True)
        libpry.raises(dump.DumpError, dump.DumpMaster, None, o, None, outfile=cs)

        t = self.tmpdir()
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
        t = self.tmpdir()
        p = os.path.join(t, "read")
        self._flowfile(p)
        assert "GET" in self._dummy_cycle(0, None, "", verbosity=1, rfile=p)

        libpry.raises(
            dump.DumpError, self._dummy_cycle,
            0, None, "", verbosity=1, rfile="/nonexistent"
        )

        libpry.raises(
            dump.DumpError, self._dummy_cycle,
            0, None, "", verbosity=1, rfile="test_dump.py"
        )

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2
        libpry.raises(AttributeError, dump.Options, nonexistent = 2)

    def test_filter(self):
        assert not "GET" in self._dummy_cycle(1, "~u foo", "", verbosity=1)

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self._dummy_cycle(1, "~s", "", verbosity=i, eventlog=True)
            assert "GET" in self._dummy_cycle(1, "~s", "\x00\x00\x00", verbosity=i)
            assert "GET" in self._dummy_cycle(1, "~s", "ascii", verbosity=i)

    def test_write(self):
        d = self.tmpdir()
        p = os.path.join(d, "a")
        self._dummy_cycle(1, None, "", wfile=p, verbosity=0)
        assert len(list(flow.FlowReader(open(p)).stream())) == 1

    def test_write_err(self):
        libpry.raises(
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
            script="scripts/all.py", verbosity=0, eventlog=True
        )
        assert "XCLIENTCONNECT" in ret
        assert "XREQUEST" in ret
        assert "XRESPONSE" in ret
        assert "XCLIENTDISCONNECT" in ret
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", script="nonexistent"
        )
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", script="starterr.py"
        )

    def test_stickycookie(self):
        self._dummy_cycle(1, None, "", stickycookie = ".*")

    def test_stickyauth(self):
        self._dummy_cycle(1, None, "", stickyauth = ".*")





tests = [
    uStrFuncs(),
    uDumpMaster()
]
