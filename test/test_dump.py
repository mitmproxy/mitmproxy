from cStringIO import StringIO
import libpry
from libmproxy import dump
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



tests = [
    uDumpMaster()
]


