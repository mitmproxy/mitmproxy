import collections.abc
import copy
import difflib
import itertools
import sys
import typing

from mitmproxy.proxy2 import commands, context
from mitmproxy.proxy2 import events
from mitmproxy.proxy2.context import ConnectionState
from mitmproxy.proxy2.events import command_reply_subclasses
from mitmproxy.proxy2.layer import Layer, NextLayer

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
        if isinstance(y, _Placeholder):
            x, y = y, x
        if isinstance(x, _Placeholder):
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
    if isinstance(a, collections.abc.Iterable) and isinstance(b, collections.abc.Iterable):
        return all(
            _eq(x, y) for x, y in itertools.zip_longest(a, b)
        )
    return _eq(a, b)


def _fmt_entry(x: TPlaybookEntry):
    arrow = ">>" if isinstance(x, events.Event) else "<<"
    x = str(x) \
        .replace('Placeholder:None', '<unset placeholder>') \
        .replace('Placeholder:', '')
    return f"{arrow} {x}"


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
    layer: Layer
    """The base layer"""
    expected: TPlaybook
    """expected command/event sequence"""
    actual: TPlaybook
    """actual command/event sequence"""
    _errored: bool
    """used to check if playbook as been fully asserted"""
    logs: bool
    """If False, the playbook specification doesn't contain log commands."""
    hooks: bool
    """If False, the playbook specification doesn't include hooks or hook replies. They are automatically replied to."""

    def __init__(
            self,
            layer: Layer,
            hooks: bool = True,
            logs: bool = False,
            expected: typing.Optional[TPlaybook] = None,
    ):
        if expected is None:
            expected = [
                events.Start()
            ]

        self.layer = layer
        self.expected = expected
        self.actual = []
        self._errored = False
        self.logs = logs
        self.hooks = hooks

    def __rshift__(self, e):
        """Add an event to send"""
        assert isinstance(e, events.Event)
        if not self.hooks and isinstance(e, events.HookReply):
            raise ValueError(f"Playbook must not contain hook replies if hooks=False: {e}")
        self.expected.append(e)
        return self

    def __lshift__(self, c):
        """Add an expected command"""
        if c is None:
            return self
        assert isinstance(c, commands.Command)
        if not self.logs and isinstance(c, commands.Log):
            raise ValueError(f"Playbook must not contain log commands if logs=False: {c}")
        if not self.hooks and isinstance(c, commands.Hook):
            raise ValueError(f"Playbook must not contain hook commands if hooks=False: {c}")
        self.expected.append(c)
        return self

    def __bool__(self):
        """Determine if playbook is correct."""
        already_asserted = len(self.actual)
        i = already_asserted
        while i < len(self.expected):
            x = self.expected[i]
            if isinstance(x, commands.Command):
                pass
            else:
                if hasattr(x, "playbook_eval"):
                    x = self.expected[i] = x.playbook_eval(self)
                if isinstance(x, events.OpenConnectionReply) and not x.reply:
                    x.command.connection.state = ConnectionState.OPEN
                elif isinstance(x, events.ConnectionClosed):
                    x.connection.state &= ~ConnectionState.CAN_READ

                self.actual.append(x)
                cmds = list(self.layer.handle_event(x))
                self.actual.extend(cmds)
                if not self.logs:
                    for offset, cmd in enumerate(cmds):
                        if isinstance(cmd, commands.Log):
                            self.expected.insert(i + 1 + offset, cmd)
                if not self.hooks:
                    last_cmd = self.actual[-1]
                    if isinstance(last_cmd, commands.Hook):
                        self.expected.insert(i + len(cmds), last_cmd)
                        self.expected.insert(i + len(cmds) + 1, events.HookReply(last_cmd))
            i += 1

        if not eq(self.expected, self.actual):
            self._errored = True
            diff = "\n".join(difflib.ndiff(
                [_fmt_entry(x) for x in self.expected],
                [_fmt_entry(x) for x in self.actual]
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


class reply(events.Event):
    args: typing.Tuple[typing.Any, ...]
    to: typing.Union[commands.Command, int]
    side_effect: typing.Callable[[typing.Any], typing.Any]

    def __init__(
            self,
            *args,
            to: typing.Union[commands.Command, int] = -1,
            side_effect: typing.Callable[[typing.Any], None] = lambda x: None
    ):
        """Utility method to reply to the latest hook in playbooks."""
        self.args = args
        self.to = to
        self.side_effect = side_effect

    def playbook_eval(self, playbook: playbook) -> events.CommandReply:
        if isinstance(self.to, int):
            expected = playbook.expected[:playbook.expected.index(self)]
            assert abs(self.to) < len(expected)
            to = expected[self.to]
            if not isinstance(to, commands.Command):
                raise AssertionError(f"There is no command at offset {self.to}: {to}")
            else:
                self.to = to
        for cmd in reversed(playbook.actual):
            if eq(self.to, cmd):
                self.to = cmd
                break
        else:
            actual_str = "\n".join(_fmt_entry(x) for x in playbook.actual)
            raise AssertionError(f"Expected command ({self.to}) did not occur:\n{actual_str}")

        assert isinstance(self.to, commands.Command)
        self.side_effect(self.to)
        reply_cls = command_reply_subclasses[type(self.to)]
        try:
            inst = reply_cls(self.to, *self.args)
        except TypeError as e:
            raise ValueError(f"Cannot instantiate {reply_cls.__name__}: {e}")
        return inst


class _Placeholder:
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

    def __str__(self):
        return f"Placeholder:{str(self.obj)}"


# noinspection PyPep8Naming
def Placeholder() -> typing.Any:
    return _Placeholder()


class EchoLayer(Layer):
    """Echo layer that sends all data back to the client in lowercase."""

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived):
            yield commands.SendData(event.connection, event.data.lower())


def next_layer(
        layer: typing.Union[typing.Type[Layer], typing.Callable[[context.Context], Layer]],
        *args,
        **kwargs
) -> reply:
    """
    Helper function to simplify the syntax for next_layer events from this:

            << commands.Hook("next_layer", next_layer)
        )
        next_layer().layer = tutils.EchoLayer(next_layer().context)
        assert (
            playbook
            >> events.HookReply(-1)

    to this:

        << commands.Hook("next_layer", next_layer)
        >> tutils.next_layer(next_layer, tutils.EchoLayer)
    """

    def set_layer(hook: commands.Hook) -> None:
        assert isinstance(hook.data, NextLayer)
        hook.data.layer = layer(hook.data.context)

    return reply(*args, side_effect=set_layer, **kwargs)
