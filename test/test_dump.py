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

    def test_basic_verbosities(self):
        for i in (1, 2, 3):
            cs = StringIO()
            m = dump.DumpMaster(None, i, cs)
            self._dummy_cycle(m)
            assert "GET" in cs.getvalue()



tests = [
    uDumpMaster()
]


