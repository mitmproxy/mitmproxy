import typing

from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.test import tutils
from mitmproxy.proxy.protocol2.utils import expect


class TEvent(events.Event):
    commands: typing.Iterable[typing.Any]

    def __init__(self, cmds=(None,)):
        self.commands = cmds


class TCommand(commands.Command):
    x: typing.Any

    def __init__(self, x=None):
        self.x = x


class TLayer(Layer):
    """
    Simple echo layer
    """

    @expect(TEvent)
    def _handle_event(self, event: TEvent) -> commands.TCommandGenerator:
        for x in event.commands:
            yield TCommand(x)


def test_playbook_simple(tctx):
    playbook = tutils.playbook(TLayer(tctx), [])
    assert (
        playbook
        >> TEvent()
        << TCommand()
        >> TEvent([])
        << None
    )


def test_playbook_partial_assert(tctx):
    playbook = tutils.playbook(TLayer(tctx), [])
    playbook = (
        playbook
        >> TEvent()
        << TCommand()
    )
    assert playbook
    playbook = (
        playbook
        >> TEvent()
        << TCommand()
    )
    assert playbook
    assert len(playbook.actual) == len(playbook.playbook) == 4
