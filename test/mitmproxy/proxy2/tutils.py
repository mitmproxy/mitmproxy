import collections
import copy
import difflib
import itertools
import typing

from mitmproxy.proxy2 import commands
from mitmproxy.proxy2 import events
from mitmproxy.proxy2 import layer
from mitmproxy.proxy2.layer import Layer

TPlaybookEntry = typing.Union[commands.Command, events.Event]
TPlaybook = typing.List[TPlaybookEntry]


def _eq(
        a: TPlaybookEntry,
        b: TPlaybookEntry
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


def eq(
        a: typing.Union[TPlaybookEntry, typing.Iterable[TPlaybookEntry]],
        b: typing.Union[TPlaybookEntry, typing.Iterable[TPlaybookEntry]]
):
    """
    Compare an indiviual event/command or a list of events/commands.
    """
    if isinstance(a, collections.Iterable) and isinstance(b, collections.Iterable):
        return all(
            _eq(x, y) for x, y in itertools.zip_longest(a, b)
        )
    return _eq(a, b)


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

        if not eq(self.expected, self.actual):
            self._errored = True

            def _str(x):
                arrow = ">" if isinstance(x, events.Event) else "<"
                x = str(x).replace('Placeholder:', '')
                return f"{arrow} {x}"

            diff = "\n".join(difflib.ndiff(
                [_str(x) for x in self.expected],
                [_str(x) for x in self.actual]
            ))
            raise AssertionError(f"Playbook mismatch!\n{diff}")
        else:
            return True

    def __del__(self):
        # Playbooks are only executed on assert (which signals that the playbook is partially
        # complete), so we need to signal if someone forgets to assert and playbooks aren't
        # evaluated.
        is_final_destruct = not hasattr(self, "_errored")
        if is_final_destruct or (not self._errored and len(self.actual) < len(self.expected)):
            raise RuntimeError("Unfinished playbook!")

    def fork(self):
        """
        Fork the current playbook to assert a second execution stream from here on.
        Returns a new playbook instance.
        """
        return copy.deepcopy(self)


class Placeholder:
    """
    Placeholder value in playbooks, so that objects (flows in particular) can be referenced before
    they are known. Example:

    f = Placeholder()
    assert (
        playbook(tcp.TCPLayer(tctx))
        << commands.Hook("tcp_start", f)  # the flow object returned here is generated by the layer.
    )

    # We can obtain the flow object now using f():
    assert f().messages == 0
    """

    def __init__(self):
        self.obj = None

    def __call__(self):
        """Get the actual object"""
        return self.obj

    def __repr__(self):
        return f"Placeholder:{repr(self.obj)}"


class EchoLayer(Layer):
    """Echo layer that sends all data back to the client in lowercase."""
    def _handle_event(self, event: events.Event):
        if isinstance(event, events.DataReceived):
            yield commands.SendData(event.connection, event.data.lower())
