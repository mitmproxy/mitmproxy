import os
from cStringIO import StringIO
import libpry
from libmproxy import dump, flow
import utils


class uDumpMaster(libpry.AutoTree):
    def _cycle(self, m, content):
        req = utils.treq()
        req.content = content
        cc = req.client_conn
        resp = utils.tresp(req)
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






tests = [
    uDumpMaster()
]
