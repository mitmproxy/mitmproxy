from dataclasses import dataclass

import pytest

from mitmproxy import connection
from mitmproxy.hooks import all_hooks
from mitmproxy.proxy import commands


@pytest.fixture
def tconn() -> connection.Server:
    return connection.Server(address=None)


def test_dataclasses(tconn):
    assert repr(commands.RequestWakeup(58))
    assert repr(commands.SendData(tconn, b"foo"))
    assert repr(commands.OpenConnection(tconn))
    assert repr(commands.CloseConnection(tconn))
    assert repr(commands.CloseTcpConnection(tconn, half_close=True))
    assert repr(commands.Log("hello"))


def test_start_hook():
    with pytest.raises(TypeError):
        commands.StartHook()

    @dataclass
    class TestHook(commands.StartHook):
        data: bytes

    f = TestHook(b"foo")
    assert f.args() == [b"foo"]
    assert TestHook in all_hooks.values()


def test_await_unwrap():
    async def awaitable():
        return 42

    command = commands.Await(awaitable())
    generator = command.unwrap()

    assert next(generator) is command
    with pytest.raises(StopIteration) as done:
        generator.send((42, None))
    assert done.value.value == 42

    command.awaitable.close()


def test_await_unwrap_error():
    error = RuntimeError("test error")

    async def awaitable():
        return None

    command = commands.Await(awaitable())

    generator = command.unwrap()
    assert next(generator) is command
    with pytest.raises(RuntimeError, match="test error"):
        generator.send((None, error))

    command.awaitable.close()
