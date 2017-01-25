from mitmproxy.addons import termlog
from mitmproxy import log
from mitmproxy.tools import dump


class TestTermLog:
    def test_simple(self, capsys):
        t = termlog.TermLog()
        t.configure(dump.Options(verbosity = 2), set([]))
        t.log(log.LogEntry("one", "info"))
        t.log(log.LogEntry("two", "debug"))
        t.log(log.LogEntry("three", "warn"))
        t.log(log.LogEntry("four", "error"))
        out, err = capsys.readouterr()
        assert "one" in out
        assert "two" not in out
        assert "three" in out
        assert "four" in err
