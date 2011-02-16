import os
from cStringIO import StringIO
import libpry
from libmproxy import dump, flow
import utils


class uDumpMaster(libpry.AutoTree):
    def _dummy_cycle(self, m):
        req = utils.treq()
        cc = req.client_conn
        resp = utils.tresp(req)
        m.handle_clientconnection(cc)
        m.handle_request(req)
        m.handle_response(resp)

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2
        libpry.raises(AttributeError, dump.Options, nonexistent = 2)

    def test_basic_verbosities(self):
        for i in (1, 2, 3):
            cs = StringIO()
            o = dump.Options(
                verbosity = i
            )
            m = dump.DumpMaster(None, o, cs)
            self._dummy_cycle(m)
            assert "GET" in cs.getvalue()

    def test_write(self):
        d = self.tmpdir()
        p = os.path.join(d, "a")
        o = dump.Options(
            wfile = p,
            verbosity = 0
        )
        cs = StringIO()
        m = dump.DumpMaster(None, o, cs)
        self._dummy_cycle(m)
        del m
        assert len(list(flow.FlowReader(open(p)).stream())) == 1

    def test_write_err(self):
        o = dump.Options(
            wfile = "nonexistentdir/foo",
            verbosity = 0
        )
        cs = StringIO()
        libpry.raises(dump.DumpError, dump.DumpMaster, None, o, cs)






tests = [
    uDumpMaster()
]


