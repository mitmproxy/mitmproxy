from dataclasses import dataclass

import pytest

from mitmproxy import event_hooks


def test_event():
    with pytest.raises(TypeError, match="may not be instantiated directly"):
        event_hooks.EventHook()

    class NoDataClass(event_hooks.EventHook):
        pass

    with pytest.raises(TypeError, match="not a dataclass"):
        NoDataClass()

    @dataclass
    class FooEventHook(event_hooks.EventHook):
        data: bytes

    e = FooEventHook(b"foo")
    assert repr(e)
    assert e.args() == [b"foo"]
    assert FooEventHook in event_hooks.all_events.values()

    with pytest.raises(RuntimeError, match="Two conflicting event classes"):
        @dataclass
        class FooEventHook2(event_hooks.EventHook):
            name = "foo"

    @dataclass
    class AnotherABC(event_hooks.EventHook):
        name = ""

    assert AnotherABC not in event_hooks.all_events.values()