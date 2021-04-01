from dataclasses import dataclass

import pytest

from mitmproxy import connection
from mitmproxy.hooks import all_hooks
from mitmproxy.proxy import commands


@pytest.fixture
def tconn() -> connection.Server:
    return connection.Server(None)


def test_dataclasses(tconn):
    assert repr(commands.SendData(tconn, b"foo"))
    assert repr(commands.OpenConnection(tconn))
    assert repr(commands.CloseConnection(tconn))
    assert repr(commands.GetSocket(tconn))
    assert repr(commands.Log("hello", "info"))


def test_start_hook():
    with pytest.raises(TypeError):
        commands.StartHook()

    @dataclass
    class TestHook(commands.StartHook):
        data: bytes

    f = TestHook(b"foo")
    assert f.args() == [b"foo"]
    assert TestHook in all_hooks.values()
