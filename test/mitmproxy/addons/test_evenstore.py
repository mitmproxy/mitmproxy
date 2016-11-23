import mock
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
    store.log(log.LogEntry("test", "info"))
    assert store.data

    assert sig_add.called
    assert not sig_refresh.called

    # test .clear()
    sig_add.reset_mock()

    store.clear()
    assert not store.data

    assert not sig_add.called
    assert sig_refresh.called
