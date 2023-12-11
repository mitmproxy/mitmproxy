from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pytest

from . import tutils
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer


class TEvent(events.Event):
    commands: Iterable[Any]

    def __init__(self, cmds=(None,)):
        self.commands = cmds


class TCommand(commands.Command):
    x: Any

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
    tplaybook >> TEvent()
    tplaybook << TCommand()
    tplaybook >> TEvent([])
    tplaybook << None
    assert tplaybook


def test_mismatch(tplaybook):
    with pytest.raises(AssertionError, match="Playbook mismatch"):
        tplaybook >> TEvent([])
        tplaybook << TCommand()
        assert tplaybook


def test_partial_assert(tplaybook):
    """Developers can assert parts of a playbook and the continue later on."""
    tplaybook >> TEvent()
    tplaybook << TCommand()
    assert tplaybook

    tplaybook >> TEvent()
    tplaybook << TCommand()
    assert tplaybook

    assert len(tplaybook.actual) == len(tplaybook.expected) == 4


@pytest.mark.parametrize("typed", [True, False])
def test_placeholder(tplaybook, typed):
    """Developers can specify placeholders for yet unknown attributes."""
    if typed:
        f = tutils.Placeholder(int)
    else:
        f = tutils.Placeholder()
    tplaybook >> TEvent([42])
    tplaybook << TCommand(f)
    assert tplaybook
    assert f() == 42


def test_placeholder_type_mismatch(tplaybook):
    """Developers can specify placeholders for yet unknown attributes."""
    f = tutils.Placeholder(str)
    with pytest.raises(
        TypeError, match="Placeholder type error for TCommand.x: expected str, got int."
    ):
        tplaybook >> TEvent([42])
        tplaybook << TCommand(f)
        assert tplaybook


def test_unfinished(tplaybook):
    """We show a warning when playbooks aren't asserted."""
    tplaybook >> TEvent()
    with pytest.raises(RuntimeError, match="Unfinished playbook"):
        tplaybook.__del__()
    tplaybook._errored = True
    tplaybook.__del__()


def test_command_reply(tplaybook):
    """CommandReplies can use relative offsets to point to the matching command."""
    tplaybook >> TEvent()
    tplaybook << TCommand()
    tplaybook >> tutils.reply()
    assert tplaybook
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

    tplaybook >> TEvent([1])
    tplaybook << command1
    tplaybook >> TEvent([2])
    tplaybook << command2

    if swap:
        tplaybook >> tutils.reply(to=command1)
        tplaybook >> tutils.reply(to=command2)
    else:
        tplaybook >> tutils.reply(to=command2)
        tplaybook >> tutils.reply(to=command1)
    assert tplaybook
    assert a() == 1
    assert b() == 2
