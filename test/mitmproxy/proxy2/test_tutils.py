import typing

import pytest

from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.layer import Layer
from . import tutils


class TEvent(events.Event):
    commands: typing.Iterable[typing.Any]

    def __init__(self, cmds=(None,)):
        self.commands = cmds


class TCommand(commands.Command):
    x: typing.Any

    def __init__(self, x=None):
        self.x = x


class TCommandReply(events.CommandReply):
    pass


class TLayer(Layer):
    """
    Simple echo layer
    """

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, TEvent):
            for x in event.commands:
                yield TCommand(x)


@pytest.fixture
def tplaybook(tctx):
    return tutils.playbook(TLayer(tctx), [])


def test_simple(tplaybook):
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
        >> TEvent([])
        << None
    )


def test_mismatch(tplaybook):
    with pytest.raises(AssertionError, message="Playbook mismatch"):
        assert (
            tplaybook
            >> TEvent([])
            << TCommand()
        )


def test_partial_assert(tplaybook):
    """Developers can assert parts of a playbook and the continue later on."""
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
    )
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
    )
    assert len(tplaybook.actual) == len(tplaybook.expected) == 4


def test_placeholder(tplaybook):
    """Developers can specify placeholders for yet unknown attributes."""
    f = tutils.Placeholder()
    assert (
        tplaybook
        >> TEvent([42])
        << TCommand(f)
    )
    assert f() == 42


def test_fork(tplaybook):
    """Playbooks can be forked to test multiple execution streams."""
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
    )
    p2 = tplaybook.fork()
    p3 = tplaybook.fork()
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
    )
    assert (
        p2
        >> TEvent()
        << TCommand()
    )
    assert len(tplaybook.actual) == len(tplaybook.expected) == 4
    assert len(p2.actual) == len(p2.expected) == 4
    assert len(p3.actual) == len(p3.expected) == 2


def test_fork_placeholder(tplaybook):
    """Forks require new placeholders."""
    f = tutils.Placeholder()
    flow = object()
    assert (
        tplaybook
        >> TEvent([flow])
        << TCommand(f)
    )
    assert f() == flow
    p2 = tplaybook.fork()

    p2_flow = p2.expected[0].commands[0]
    assert p2_flow != flow

    # As we have forked, we need a new placeholder.
    f2 = tutils.Placeholder()
    assert (
        p2
        >> TEvent([p2_flow])
        << TCommand(f2)
    )
    assert f2() == p2_flow

    # re-using the old placeholder does not work.
    with pytest.raises(AssertionError, message="Playbook mismatch"):
        assert (
            p2
            >> TEvent([p2_flow])
            << TCommand(f)
        )


def test_unfinished(tplaybook):
    """We show a warning when playbooks aren't asserted."""
    tplaybook >> TEvent()
    with pytest.raises(RuntimeError, message="Unfinished playbook"):
        tplaybook.__del__()
    tplaybook._errored = True
    tplaybook.__del__()


def test_command_reply(tplaybook):
    """CommandReplies can use relative offsets to point to the matching command."""
    assert (
        tplaybook
        >> TEvent()
        << TCommand()
        >> TCommandReply(-1, 42)
    )
    assert tplaybook.actual[1] == tplaybook.actual[2].command


def test_default_playbook(tctx):
    p = tutils.playbook(TLayer(tctx))
    assert p
    assert len(p.actual) == 1
    assert isinstance(p.actual[0], events.Start)


def test_eq_blocking():
    """_eq should not consider differences in .blocking"""
    a = TCommand()
    a.blocking = True
    b = TCommand()
    b.blocking = False
    assert tutils._eq(a, b)


def test_eq_placeholder():
    """_eq should assign placeholders."""
    a = TCommand()
    a.foo = 42
    a.bar = tutils.Placeholder()
    b = TCommand()
    b.foo = tutils.Placeholder()
    b.bar = 43
    assert tutils._eq(a, b)
    assert a.foo == b.foo() == 42
    assert a.bar() == b.bar == 43

    b.foo.obj = 44
    assert not tutils._eq(a, b)
