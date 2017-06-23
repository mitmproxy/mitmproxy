import itertools
import typing

from mitmproxy.proxy.protocol2 import commands
from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2 import layer


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
    playbook: typing.List[typing.Union[commands.Command, events.Event]]

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

    def __rshift__(self, e):
        """Add an event to send"""
        assert isinstance(e, events.Event)
        self.playbook.append(e)
        return self

    def __lshift__(self, c):
        """Add an expected command"""
        if c is None:
            return self
        assert isinstance(c, commands.Command)
        self.playbook.append(c)
        return self

    def __bool__(self):
        """Determine if playbook is correct."""
        actual = []
        for i, x in enumerate(self.playbook):
            if isinstance(x, commands.Command):
                pass
            else:
                if isinstance(x, events.CommandReply):
                    if isinstance(x.command, int):
                        x.command = actual[i + x.command]

                actual.append(x)
                actual.extend(
                    self.layer.handle_event(x)
                )

        if actual != self.playbook:
            # print debug info
            for a, e in itertools.zip_longest(actual, self.playbook):
                if a == e:
                    print(f"= {e}")
                else:
                    print(f"✓ {e}")
                    print(f"✗ {a}")
            return False
        return True
