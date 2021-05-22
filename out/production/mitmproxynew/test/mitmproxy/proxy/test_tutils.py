import typing
from dataclasses import dataclass

import pytest

from mitmproxy.proxy import commands, events, layer
from . import tutils


class TEvent(events.Event):
    commands: typing.Iterable[typing.Any]

    def __init__(self, cmds=(None,)):
        self.commands = cmds


class TCommand(commands.Command):
    x: typing.Any

    def __init__(self, x=None):
        self.x = x


@dataclass
class TCommandCompleted(events.CommandCompleted):
    command: TCommand


class TLayer(layer.Layer):
    """
    Simple echo layer
    """

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, TEvent):
            for x in event.commands:
                yield TCommand(x)


@pytest.fixture
def tplaybook(tctx):
    return tutils.Playbook(TLayer(tctx), expected=[])


def test_simple(tplaybook):
    assert (
            tplaybook
            >> TEvent()
            << TCommand()
            >> TEvent([])
            << None
    )


def test_mismatch(tplaybook):
    with pytest.raises(AssertionError, match="Playbook mismatch"):
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


@pytest.mark.parametrize("typed", [True, False])
def test_placeholder(tplaybook, typed):
    """Developers can specify placeholders for yet unknown attributes."""
    if typed:
        f = tutils.Placeholder(int)
    else:
        f = tutils.Placeholder()
    assert (
            tplaybook
            >> TEvent([42])
            << TCommand(f)
    )
    assert f() == 42


def test_placeholder_type_mismatch(tplaybook):
    """Developers can specify placeholders for yet unknown attributes."""
    f = tutils.Placeholder(str)
    with pytest.raises(TypeError, match="Placeholder type error for TCommand.x: expected str, got int."):
        assert (
                tplaybook
                >> TEvent([42])
                << TCommand(f)
        )


def test_unfinished(tplaybook):
    """We show a warning when playbooks aren't asserted."""
    tplaybook >> TEvent()
    with pytest.raises(RuntimeError, match="Unfinished playbook"):
        tplaybook.__del__()
    tplaybook._errored = True
    tplaybook.__del__()


def test_command_reply(tplaybook):
    """CommandReplies can use relative offsets to point to the matching command."""
    assert (
            tplaybook
            >> TEvent()
            << TCommand()
            >> tutils.reply()
    )
    assert tplaybook.actual[1] == tplaybook.actual[2].command


def test_default_playbook(tctx):
    p = tutils.Playbook(TLayer(tctx))
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

    b.foo._obj = 44
    assert not tutils._eq(a, b)


@pytest.mark.parametrize("swap", [False, True])
def test_command_multiple_replies(tplaybook, swap):
    a = tutils.Placeholder(int)
    b = tutils.Placeholder(int)

    command1 = TCommand(a)
    command2 = TCommand(b)

    (tplaybook
     >> TEvent([1])
     << command1
     >> TEvent([2])
     << command2
     )
    if swap:
        tplaybook >> tutils.reply(to=command1)
        tplaybook >> tutils.reply(to=command2)
    else:
        tplaybook >> tutils.reply(to=command2)
        tplaybook >> tutils.reply(to=command1)
    assert tplaybook
    assert a() == 1
    assert b() == 2
