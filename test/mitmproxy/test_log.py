from mitmproxy import log


def test_logentry():
    e = log.LogEntry("foo", "info")
    assert repr(e) == "LogEntry(foo, info)"

    f = log.LogEntry("foo", "warning")
    assert e == e
    assert e != f
    assert e != 42


def test_dont_pick_up_mutations():
    x = {"foo": "bar"}
    e = log.LogEntry(x, "info")
    x["foo"] = "baz"  # this should not affect the log entry anymore.
    assert repr(e) == "LogEntry({'foo': 'bar'}, info)"
