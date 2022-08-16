from mitmproxy import log
from mitmproxy.addons import eventstore


def test_simple():
    store = eventstore.EventStore()
    assert not store.data

    sig_add_called = False
    sig_refresh_called = False

    def sig_add(entry):
        nonlocal sig_add_called
        sig_add_called = True

    def sig_refresh():
        nonlocal sig_refresh_called
        sig_refresh_called = True

    store.sig_add.connect(sig_add)
    store.sig_refresh.connect(sig_refresh)

    assert not sig_add_called
    assert not sig_refresh_called

    # test .log()
    store.add_log(log.LogEntry("test", "info"))
    assert store.data

    assert sig_add_called
    assert not sig_refresh_called

    # test .clear()
    sig_add_called = False

    store.clear()
    assert not store.data

    assert not sig_add_called
    assert sig_refresh_called


def test_max_size():
    store = eventstore.EventStore(3)
    assert store.size == 3
    store.add_log(log.LogEntry("foo", "info"))
    store.add_log(log.LogEntry("bar", "info"))
    store.add_log(log.LogEntry("baz", "info"))
    assert len(store.data) == 3
    assert ["foo", "bar", "baz"] == [x.msg for x in store.data]

    # overflow
    store.add_log(log.LogEntry("boo", "info"))
    assert len(store.data) == 3
    assert ["bar", "baz", "boo"] == [x.msg for x in store.data]
