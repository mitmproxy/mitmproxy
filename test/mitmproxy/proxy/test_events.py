from unittest.mock import Mock

import pytest

from mitmproxy.proxy import events, context, commands


@pytest.fixture
def tconn() -> context.Server:
    return context.Server(None)


def test_dataclasses(tconn):
    assert repr(events.Start())
    assert repr(events.DataReceived(tconn, b"foo"))
    assert repr(events.ConnectionClosed(tconn))


def test_commandreply():
    with pytest.raises(TypeError):
        events.CommandReply()
    assert repr(events.HookReply(Mock(), None))

    class FooCommand(commands.Command):
        pass

    with pytest.raises(RuntimeError, match="properly annotated"):
        class FooReply(events.CommandReply):
            pass

    class FooReply1(events.CommandReply):
        command: FooCommand

    with pytest.raises(RuntimeError, match="conflicting subclasses"):
        class FooReply2(events.CommandReply):
            command: FooCommand
