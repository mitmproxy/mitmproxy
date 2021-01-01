from dataclasses import dataclass

import pytest

from mitmproxy import events


def test_event():
    with pytest.raises(TypeError, match="may not be instantiated directly"):
        events.MitmproxyEvent()

    class NoDataClass(events.MitmproxyEvent):
        pass

    with pytest.raises(TypeError, match="not a dataclass"):
        NoDataClass()

    @dataclass
    class FooEvent(events.MitmproxyEvent):
        data: bytes

    e = FooEvent(b"foo")
    assert repr(e)
    assert e.args() == [b"foo"]
    assert FooEvent in events.all_events.values()

    with pytest.raises(RuntimeError, match="Two conflicting event classes"):
        @dataclass
        class FooEvent2(events.MitmproxyEvent):
            name = "foo"

    @dataclass
    class AnotherABC(events.MitmproxyEvent):
        name = ""

    assert AnotherABC not in events.all_events.values()