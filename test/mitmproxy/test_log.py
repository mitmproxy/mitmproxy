from mitmproxy import log


def test_logentry():
    e = log.LogEntry("foo", "info")
    assert repr(e) == "LogEntry(foo, info)"
