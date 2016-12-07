import io

from mitmproxy.addons import termlog
from mitmproxy import log
from mitmproxy.tools import dump


class TestTermLog:
    def test_simple(self):
        sio = io.StringIO()
        t = termlog.TermLog(outfile=sio)
        t.configure(dump.Options(verbosity = 2), set([]))
        t.log(log.LogEntry("one", "info"))
        assert "one" in sio.getvalue()
        t.log(log.LogEntry("two", "debug"))
        assert "two" not in sio.getvalue()
