import os
from cStringIO import StringIO
import libpry
from libmproxy import dump, flow
import tutils

class uStrFuncs(libpry.AutoTree):
    def test_all(self):
        t = tutils.tresp()
        t.set_replay()
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
        resp = tutils.tresp(req)
        resp.content = content
        m.handle_clientconnect(cc)
        m.handle_request(req)
        m.handle_response(resp)

    def _dummy_cycle(self, filt, content, **options):
        cs = StringIO()
        o = dump.Options(**options)
        m = dump.DumpMaster(None, o, filt, outfile=cs)
        self._cycle(m, content)
        return cs.getvalue()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay="nonexistent", kill=True)
        libpry.raises(dump.DumpError, dump.DumpMaster, None, o, None, outfile=cs)

        t = self.tmpdir()
        p = os.path.join(t, "rep")
        f = open(p, "w")
        fw = flow.FlowWriter(f)
        t = tutils.tflow_full()
        t.response = tutils.tresp(t.request)
        fw.add(t)
        f.close()

        o = dump.Options(server_replay=p, kill=True)
        m = dump.DumpMaster(None, o, None, outfile=cs)
        
        self._cycle(m, "content")
        self._cycle(m, "content")

        o = dump.Options(server_replay=p, kill=False)
        m = dump.DumpMaster(None, o, None, outfile=cs)
        self._cycle(m, "nonexistent")

        o = dump.Options(client_replay=p, kill=False)
        m = dump.DumpMaster(None, o, None, outfile=cs)

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2
        libpry.raises(AttributeError, dump.Options, nonexistent = 2)

    def test_filter(self):
        assert not "GET" in self._dummy_cycle("~u foo", "", verbosity=1)

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self._dummy_cycle("~s", "", verbosity=i)
            assert "GET" in self._dummy_cycle("~s", "\x00\x00\x00", verbosity=i)
            assert "GET" in self._dummy_cycle("~s", "ascii", verbosity=i)

    def test_write(self):
        d = self.tmpdir()
        p = os.path.join(d, "a")
        self._dummy_cycle(None, "", wfile=p, verbosity=0)
        assert len(list(flow.FlowReader(open(p)).stream())) == 1

    def test_write_err(self):
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle,
            None,
            "", 
            wfile = "nonexistentdir/foo"
        )

    def test_request_script(self):
        ret = self._dummy_cycle(None, "", request_script="scripts/a", verbosity=1)
        assert "TESTOK" in ret
        assert "DEBUG" in ret
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, None, "", request_script="nonexistent"
        )
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, None, "", request_script="scripts/err_return"
        )

    def test_response_script(self):
        ret = self._dummy_cycle(None, "", response_script="scripts/a", verbosity=1)
        assert "TESTOK" in ret
        assert "DEBUG" in ret
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, None, "", response_script="nonexistent"
        )
        libpry.raises(
            dump.DumpError,
            self._dummy_cycle, None, "", response_script="scripts/err_return"
        )

    def test_stickycookie(self):
        ret = self._dummy_cycle(None, "", stickycookie = ".*")






tests = [
    uStrFuncs(),
    uDumpMaster()
]
