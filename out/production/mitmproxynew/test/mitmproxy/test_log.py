from mitmproxy import log


def test_logentry():
    e = log.LogEntry("foo", "info")
    assert repr(e) == "LogEntry(foo, info)"

    f = log.LogEntry("foo", "warning")
    assert e == e
    assert e != f
    assert e != 42
