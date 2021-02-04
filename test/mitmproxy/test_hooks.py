from dataclasses import dataclass

import pytest

from mitmproxy import hooks


def test_hook():
    with pytest.raises(TypeError, match="may not be instantiated directly"):
        hooks.Hook()

    class NoDataClass(hooks.Hook):
        pass

    with pytest.raises(TypeError, match="not a dataclass"):
        NoDataClass()

    @dataclass
    class FooHook(hooks.Hook):
        data: bytes

    e = FooHook(b"foo")
    assert repr(e)
    assert e.args() == [b"foo"]
    assert FooHook in hooks.all_hooks.values()

    with pytest.warns(RuntimeWarning, match="Two conflicting event classes"):
        @dataclass
        class FooHook2(hooks.Hook):
            name = "foo"

    @dataclass
    class AnotherABC(hooks.Hook):
        name = ""

    assert AnotherABC not in hooks.all_hooks.values()