from .. import mastertest
import io

from mitmproxy.addons import termlog
from mitmproxy import log
from mitmproxy.tools import dump


class TestTermLog(mastertest.MasterTest):
    def test_simple(self):
        t = termlog.TermLog()
        sio = io.StringIO()
        t.configure(dump.Options(tfile = sio, verbosity = 2), set([]))
        t.log(log.LogEntry("one", "info"))
        assert "one" in sio.getvalue()
        t.log(log.LogEntry("two", "debug"))
        assert "two" not in sio.getvalue()
