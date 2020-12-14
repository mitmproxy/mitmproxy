import pytest

from mitmproxy.proxy import commands, context


@pytest.fixture
def tconn() -> context.Server:
    return context.Server(None)


def test_dataclasses(tconn):
    assert repr(commands.SendData(tconn, b"foo"))
    assert repr(commands.OpenConnection(tconn))
    assert repr(commands.CloseConnection(tconn))
    assert repr(commands.GetSocket(tconn))
    assert repr(commands.Log("hello", "info"))


def test_hook():
    with pytest.raises(TypeError):
        commands.Hook()

    class FooHook(commands.Hook):
        data: bytes

    f = FooHook(b"foo")
    assert repr(f)
    assert f.args() == [b"foo"]
    assert FooHook in commands.all_hooks.values()

    with pytest.raises(RuntimeError, match="Two conflicting hooks"):
        class FooHook2(commands.Hook):
            name = "foo"
