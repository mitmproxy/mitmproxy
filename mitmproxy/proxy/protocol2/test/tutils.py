import difflib
import itertools
import re
import typing

import copy

from mitmproxy.proxy.protocol2 import commands
from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2 import layer

TPlaybookEntry = typing.Union[commands.Command, events.Event]
TPlaybook = typing.List[TPlaybookEntry]


def _eq(
        a: typing.Union[commands.Command, events.Event],
        b: typing.Union[commands.Command, events.Event]
) -> bool:
    """Compare two commands/events, and possibly update placeholders."""
    if type(a) != type(b):
        return False

    a = a.__dict__
    b = b.__dict__
    # we can assume a.keys() == b.keys()
    for k in a:
        if k == "blocking":
            continue
        x, y = a[k], b[k]

        # if there's a placeholder, make it x.
        if isinstance(y, Placeholder):
            x, y = y, x
        if isinstance(x, Placeholder):
            if x.obj is None:
                x.obj = y
            x = x.obj
        if x != y:
            return False

    return True


class playbook:
    """
    Assert that a layer emits the expected commands in reaction to a given sequence of events.
    For example, the following code asserts that the TCP layer emits an OpenConnection command
    immediately after starting and does not yield any further commands as a reaction to successful
    connection establishment.

    assert playbook(tcp.TCPLayer(tctx)) \
        << commands.OpenConnection(tctx.server)
        >> events.OpenConnectionReply(-1, "ok")  # -1 = reply to command in previous line.
        << None  # this line is optional.

    This is syntactic sugar for the following:

    t = tcp.TCPLayer(tctx)
    x1 = list(t.handle_event(events.Start()))
    assert x1 == [commands.OpenConnection(tctx.server)]
    x2 = list(t.handle_event(events.OpenConnectionReply(x1[-1])))
    assert x2 == []
    """
    layer: layer.Layer
    """The base layer"""
    playbook: TPlaybook
    """expected command/event sequence"""
    actual: TPlaybook
    """actual command/event sequence"""
    _final: bool
    """True if no << or >> operation has been called on this."""

    def __init__(
            self,
            layer,
            playbook=None,
    ):
        if playbook is None:
            playbook = [
                events.Start()
            ]

        self.layer = layer
        self.playbook = playbook
        self.actual = []
        self._final = True

    def _copy_with(self, entry: TPlaybookEntry):
        self._final = False
        p = playbook(
            self.layer,
            self.playbook + [entry]
        )
        p.actual = self.actual.copy()
        return p

    def __rshift__(self, e):
        """Add an event to send"""
        assert isinstance(e, events.Event)
        return self._copy_with(e)

    def __lshift__(self, c):
        """Add an expected command"""
        if c is None:
            return self
        assert isinstance(c, commands.Command)
        return self._copy_with(c)

    def __bool__(self):
        """Determine if playbook is correct."""

        self.layer = copy.deepcopy(self.layer)
        self.playbook = copy.deepcopy(self.playbook)
        self.actual = copy.deepcopy(self.actual)

        already_asserted = len(self.actual)
        for i, x in enumerate(self.playbook[already_asserted:], already_asserted):
            if isinstance(x, commands.Command):
                pass
            else:
                if isinstance(x, events.CommandReply):
                    if isinstance(x.command, int) and abs(x.command) < len(self.actual):
                        x.command = self.actual[x.command]

                self.actual.append(x)
                self.actual.extend(
                    self.layer.handle_event(x)
                )

        success = all(
            _eq(e, a)
            for e, a in itertools.zip_longest(self.playbook, self.actual)
        )
        if not success:
            def _str(x):
                # add arrows to diff
                return f"{'>' if isinstance(x, events.Event) else '<'} {x}"

            diff = difflib.ndiff(
                [_str(x) for x in self.playbook],
                [_str(x) for x in self.actual]
            )
            print("✗ Playbook mismatch:")
            print("\n".join(diff))
            return False
        else:
            return True

    def __del__(self):
        if self._final and len(self.actual) < len(self.playbook):
            raise RuntimeError("Unfinished playbook!")


class Placeholder:
    """Placeholder value in playbooks, so that flows can be referenced before they are initialized."""

    def __init__(self):
        self.obj = None

    def __call__(self):
        """Get the actual object"""
        return self.obj

    def __repr__(self):
        return f"P({repr(self.obj)})"
