import io

from mitmproxy import log
from mitmproxy.addons import termlog
from mitmproxy.test import taddons


def test_output(capsys):
    t = termlog.TermLog()
    with taddons.context(t) as tctx:
        tctx.options.termlog_verbosity = "info"
        tctx.configure(t)
        t.add_log(log.LogEntry("one", "info"))
        t.add_log(log.LogEntry("two", "debug"))
        t.add_log(log.LogEntry("three", "warn"))
        t.add_log(log.LogEntry("four", "error"))
    out, err = capsys.readouterr()
    assert out.strip().splitlines() == ["one", "three"]
    assert err.strip().splitlines() == ["four"]


def test_styling() -> None:
    f = io.StringIO()
    f.isatty = lambda: True
    t = termlog.TermLog(out=f)

    with taddons.context(t) as tctx:
        tctx.configure(t)
        t.add_log(log.LogEntry("hello world", "info"))

    assert f.getvalue() == "\x1b[22mhello world\x1b[0m\n"
