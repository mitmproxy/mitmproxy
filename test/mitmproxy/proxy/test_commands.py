from dataclasses import dataclass

import pytest

from mitmproxy.event_hooks import all_events
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
        commands.StartHook()

    @dataclass
    class TestHook(commands.StartHook):
        data: bytes

    f = TestHook(b"foo")
    assert f.args() == [b"foo"]
    assert TestHook in all_events.values()
