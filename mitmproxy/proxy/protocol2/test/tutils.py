import copy
import difflib
import itertools
import typing

import re

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
    expected: TPlaybook
    """expected command/event sequence"""
    actual: TPlaybook
    """actual command/event sequence"""
    _errored: bool
    """used to check if playbook as been fully asserted"""

    def __init__(
            self,
            layer,
            expected=None,
    ):
        if expected is None:
            expected = [
                events.Start()
            ]

        self.layer = layer
        self.expected = expected
        self.actual = []
        self._errored = False

    def __rshift__(self, e):
        """Add an event to send"""
        assert isinstance(e, events.Event)
        self.expected.append(e)
        return self

    def __lshift__(self, c):
        """Add an expected command"""
        if c is None:
            return self
        assert isinstance(c, commands.Command)
        self.expected.append(c)
        return self

    def __bool__(self):
        """Determine if playbook is correct."""
        already_asserted = len(self.actual)
        for i, x in enumerate(self.expected[already_asserted:], already_asserted):
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
                for e, a in itertools.zip_longest(self.expected, self.actual)
        )
        if not success:
            self._errored = True

            def _str(x):
                x_str = re.sub(r'Placeholder\((.*?)\)', r'\1', str(x))
                return f"{'>' if isinstance(x, events.Event) else '<'} {x_str}"

            diff = "\n".join(difflib.ndiff(
                [_str(x) for x in self.expected],
                [_str(x) for x in self.actual]
            ))
            raise AssertionError(f"Playbook mismatch!\n{diff}")
        else:
            return True

    def __del__(self):
        if not self._errored and len(self.actual) < len(self.expected):
            raise RuntimeError("Unfinished playbook!")

    def fork(self):
        return copy.deepcopy(self)


class Placeholder:
    """Placeholder value in playbooks, so that flows can be referenced before they are initialized."""

    def __init__(self):
        self.obj = None

    def __call__(self):
        """Get the actual object"""
        return self.obj

    def __repr__(self):
        return f"Placeholder({repr(self.obj)})"
