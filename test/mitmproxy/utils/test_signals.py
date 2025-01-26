from unittest import mock

import pytest

from mitmproxy.utils.signals import AsyncSignal
from mitmproxy.utils.signals import SyncSignal


def test_sync_signal() -> None:
    m = mock.Mock()

    s = SyncSignal(lambda event: None)
    s.connect(m)
    s.send("foo")

    assert m.call_args_list == [mock.call("foo")]

    class Foo:
        called = None

        def bound(self, event):
            self.called = event

    f = Foo()
    s.connect(f.bound)
    s.send(event="bar")
    assert f.called == "bar"
    assert m.call_args_list == [mock.call("foo"), mock.call(event="bar")]

    s.disconnect(m)
    s.send("baz")
    assert f.called == "baz"
    assert m.call_count == 2

    def err(event):
        raise RuntimeError

    s.connect(err)
    with pytest.raises(RuntimeError):
        s.send(42)


def test_signal_weakref() -> None:
    def m1():
        pass

    def m2():
        pass

    s = SyncSignal(lambda: None)
    s.connect(m1)
    s.connect(m2)
    del m2
    s.send()
    assert len(s.receivers) == 1


def test_sync_signal_async_receiver() -> None:
    s = SyncSignal(lambda: None)

    with pytest.raises(AssertionError):
        s.connect(mock.AsyncMock())


async def test_async_signal() -> None:
    s = AsyncSignal(lambda event: None)
    m1 = mock.AsyncMock()
    m2 = mock.Mock()

    s.connect(m1)
    s.connect(m2)
    await s.send("foo")
    assert m1.call_args_list == m2.call_args_list == [mock.call("foo")]

    s.disconnect(m2)

    await s.send("bar")
    assert m1.call_count == 2
    assert m2.call_count == 1
