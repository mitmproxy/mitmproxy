from unittest.mock import Mock

import pytest

from mitmproxy import connection
from mitmproxy.proxy import events, commands


@pytest.fixture
def tconn() -> connection.Server:
    return connection.Server(None)


def test_dataclasses(tconn):
    assert repr(events.Start())
    assert repr(events.DataReceived(tconn, b"foo"))
    assert repr(events.ConnectionClosed(tconn))


def test_command_completed():
    with pytest.raises(TypeError):
        events.CommandCompleted()
    assert repr(events.HookCompleted(Mock(), None))

    class FooCommand(commands.Command):
        pass

    with pytest.warns(RuntimeWarning, match="properly annotated"):
        class FooCompleted(events.CommandCompleted):
            pass

    class FooCompleted1(events.CommandCompleted):
        command: FooCommand

    with pytest.warns(RuntimeWarning, match="conflicting subclasses"):
        class FooCompleted2(events.CommandCompleted):
            command: FooCommand
