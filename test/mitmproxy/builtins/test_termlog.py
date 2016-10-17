from .. import mastertest
import io

from mitmproxy.builtins import termlog
from mitmproxy import controller
from mitmproxy import dump


class TestTermLog(mastertest.MasterTest):
    def test_simple(self):
        t = termlog.TermLog()
        sio = io.StringIO()
        t.configure(dump.Options(tfile = sio, verbosity = 2), set([]))
        t.log(controller.LogEntry("one", "info"))
        assert "one" in sio.getvalue()
        t.log(controller.LogEntry("two", "debug"))
        assert "two" not in sio.getvalue()
