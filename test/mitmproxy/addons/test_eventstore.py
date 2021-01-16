from unittest import mock
from mitmproxy import log
from mitmproxy.addons import eventstore


def test_simple():
    store = eventstore.EventStore()
    assert not store.data

    sig_add = mock.Mock(spec=lambda: 42)
    sig_refresh = mock.Mock(spec=lambda: 42)
    store.sig_add.connect(sig_add)
    store.sig_refresh.connect(sig_refresh)

    assert not sig_add.called
    assert not sig_refresh.called

    # test .log()
    store.add_log(log.LogEntry("test", "info"))
    assert store.data

    assert sig_add.called
    assert not sig_refresh.called

    # test .clear()
    sig_add.reset_mock()

    store.clear()
    assert not store.data

    assert not sig_add.called
    assert sig_refresh.called


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
