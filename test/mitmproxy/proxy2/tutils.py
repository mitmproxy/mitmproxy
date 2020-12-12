import collections.abc
import difflib
import itertools
import re
import traceback
import typing

from mitmproxy.proxy2 import commands, context, layer
from mitmproxy.proxy2 import events
from mitmproxy.proxy2.context import ConnectionState
from mitmproxy.proxy2.events import command_reply_subclasses
from mitmproxy.proxy2.layer import Layer

PlaybookEntry = typing.Union[commands.Command, events.Event]
PlaybookEntryList = typing.List[PlaybookEntry]


def _eq(
        a: PlaybookEntry,
        b: PlaybookEntry
) -> bool:
    """Compare two commands/events, and possibly update placeholders."""
    if type(a) != type(b):
        return False

    a_dict = a.__dict__
    b_dict = b.__dict__
    # we can assume a.keys() == b.keys()
    for k in a_dict:
        if k == "blocking":
            continue
        x = a_dict[k]
        y = b_dict[k]

        # if there's a placeholder, make it x.
        if isinstance(y, _Placeholder):
            x, y = y, x
        if isinstance(x, _Placeholder):
            try:
                x = x.setdefault(y)
            except TypeError as e:
                raise TypeError(f"Placeholder type error for {type(a).__name__}.{k}: {e}")
        if x != y:
            return False

    return True


def eq(
        a: typing.Union[PlaybookEntry, typing.Iterable[PlaybookEntry]],
        b: typing.Union[PlaybookEntry, typing.Iterable[PlaybookEntry]]
):
    """
    Compare an indiviual event/command or a list of events/commands.
    """
    if isinstance(a, collections.abc.Iterable) and isinstance(b, collections.abc.Iterable):
        return all(
            _eq(x, y) for x, y in itertools.zip_longest(a, b)
        )
    return _eq(a, b)


def _fmt_entry(x: PlaybookEntry):
    arrow = ">>" if isinstance(x, events.Event) else "<<"
    x = str(x)
    x = re.sub('Placeholder:None', '<unset placeholder>', x, flags=re.IGNORECASE)
    x = re.sub('Placeholder:', '', x, flags=re.IGNORECASE)
    return f"{arrow} {x}"


def _merge_sends(lst: PlaybookEntryList) -> PlaybookEntryList:
    merged = lst[:1]
    for x in lst[1:]:
        prev = merged[-1]
        two_subsequent_sends_to_the_same_remote = (
                isinstance(x, commands.SendData) and
                isinstance(prev, commands.SendData) and
                x.connection is prev.connection
        )
        if two_subsequent_sends_to_the_same_remote:
            prev.data += x.data
        else:
            merged.append(x)
    return merged


class _TracebackInPlaybook(commands.Command):
    def __init__(self, exc):
        self.e = exc

    def __repr__(self):
        return self.e


class Playbook:
    """
    Assert that a layer emits the expected commands in reaction to a given sequence of events.
    For example, the following code asserts that the TCP layer emits an OpenConnection command
    immediately after starting and does not yield any further commands as a reaction to successful
    connection establishment.

    assert playbook(tcp.TCPLayer(tctx)) \
        << commands.OpenConnection(tctx.server)
        >> reply(None)
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
    expected: PlaybookEntryList
    """expected command/event sequence"""
    actual: PlaybookEntryList
    """actual command/event sequence"""
    _errored: bool
    """used to check if playbook as been fully asserted"""
    logs: bool
    """If False, the playbook specification doesn't contain log commands."""
    hooks: bool
    """If False, the playbook specification doesn't include hooks or hook replies. They are automatically replied to."""
    merge_sends: bool
    """If True, subsequent SendData commands to the same remote will be merged in both expected and actual playbook."""

    def __init__(
            self,
            layer: Layer,
            hooks: bool = True,
            logs: bool = False,
            expected: typing.Optional[PlaybookEntryList] = None,
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
        self.expected.append(e)
        return self

    def __lshift__(self, c):
        """Add an expected command"""
        if c is None:
            return self
        assert isinstance(c, commands.Command)

        prev = self.expected[-1]
        two_subsequent_sends_to_the_same_remote = (
                isinstance(c, commands.SendData)
                and isinstance(prev, commands.SendData)
                and prev.connection is c.connection
        )
        if two_subsequent_sends_to_the_same_remote:
            prev.data += c.data
        else:
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
                    try:
                        x = self.expected[i] = x.playbook_eval(self)
                    except Exception:
                        self.actual.append(_TracebackInPlaybook(traceback.format_exc()))
                        break
                for name, value in vars(x).items():
                    if isinstance(value, _Placeholder):
                        setattr(x, name, value())
                if isinstance(x, events.OpenConnectionReply) and not x.reply:
                    x.command.connection.state = ConnectionState.OPEN
                elif isinstance(x, events.ConnectionClosed):
                    x.connection.state &= ~ConnectionState.CAN_READ

                self.actual.append(x)
                try:
                    cmds = list(self.layer.handle_event(x))
                except Exception:
                    self.actual.append(_TracebackInPlaybook(traceback.format_exc()))
                    break
                self.actual.extend(cmds)
                pos = len(self.actual) - len(cmds) - 1
                for cmd in cmds:
                    pos += 1
                    assert self.actual[pos] == cmd
                    if isinstance(cmd, commands.CloseConnection):
                        if cmd.half_close:
                            cmd.connection.state &= ~ConnectionState.CAN_WRITE
                        else:
                            cmd.connection.state = ConnectionState.CLOSED
                    elif isinstance(cmd, commands.Log):
                        need_to_emulate_log = (
                                not self.logs and
                                cmd.level in ("debug", "info") and
                                (
                                        pos >= len(self.expected)
                                        or not isinstance(self.expected[pos], commands.Log)
                                )
                        )
                        if need_to_emulate_log:
                            self.expected.insert(pos, cmd)
                    elif isinstance(cmd, commands.Hook) and not self.hooks:
                        need_to_emulate_hook = (
                                not self.hooks
                                and (
                                        pos >= len(self.expected) or
                                        (not (
                                                isinstance(self.expected[pos], commands.Hook)
                                                and self.expected[pos].name == cmd.name
                                        ))
                                )
                        )
                        if need_to_emulate_hook:
                            self.expected.insert(pos, cmd)
                            if cmd.blocking:
                                # the current event may still have yielded more events, so we need to insert
                                # the reply *after* those additional events.
                                self.expected.insert(pos + len(cmds) - cmds.index(cmd), events.HookReply(cmd))
                    elif isinstance(cmd, commands.SendData):
                        prev = self.actual[pos - 1]
                        two_subsequent_sends_to_the_same_remote = (
                                isinstance(prev, commands.SendData) and
                                cmd.connection is prev.connection
                        )
                        if two_subsequent_sends_to_the_same_remote:
                            prev.data += cmd.data
                            self.actual.pop(pos)
                            pos -= 1
                eq(self.expected[i:], self.actual[i:])  # compare now already to set placeholders
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

    def playbook_eval(self, playbook: Playbook) -> events.CommandReply:
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
            raise AssertionError(f"Expected command {self.to} did not occur.")

        assert isinstance(self.to, commands.Command)
        if isinstance(self.to, commands.Hook):
            self.side_effect(*self.to.as_tuple())
            reply_cls = events.HookReply
        else:
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

    f = Placeholder(TCPFlow)
    assert (
        playbook(tcp.TCPLayer(tctx))
        << TcpStartHook(f)  # the flow object returned here is generated by the layer.
    )

    # We can obtain the flow object now using f():
    assert f().messages == 0
    """

    def __init__(self, cls: typing.Type):
        self._obj = None
        self._cls = cls

    def __call__(self):
        """Get the actual object"""
        return self._obj

    def setdefault(self, value):
        if self._obj is None:
            if self._cls is not typing.Any and not isinstance(value, self._cls):
                raise TypeError(f"expected {self._cls.__name__}, got {type(value).__name__}.")
            self._obj = value
        return self._obj

    def __repr__(self):
        return f"Placeholder:{repr(self._obj)}"

    def __str__(self):
        return f"Placeholder:{str(self._obj)}"


T = typing.TypeVar("T")


# noinspection PyPep8Naming
def Placeholder(cls: typing.Type[T] = typing.Any) -> typing.Union[T, typing.Callable[[], T]]:
    return _Placeholder(cls)


class EchoLayer(Layer):
    """Echo layer that sends all data back to the client in lowercase."""

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            yield commands.SendData(event.connection, event.data.lower())
        if isinstance(event, events.ConnectionClosed):
            yield commands.CloseConnection(event.connection)


class RecordLayer(Layer):
    """Layer that records all events but does nothing."""
    event_log: typing.List[events.Event]

    def __init__(self, context: context.Context) -> None:
        super().__init__(context)
        self.event_log = []

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        self.event_log.append(event)
        yield from ()


def reply_next_layer(
        child_layer: typing.Union[typing.Type[Layer], typing.Callable[[context.Context], Layer]],
        *args,
        **kwargs
) -> reply:
    """Helper function to simplify the syntax for next_layer events to this:
        << commands.Hook("next_layer", next_layer)
        >> tutils.next_layer(next_layer, tutils.EchoLayer)
    """

    def set_layer(next_layer: layer.NextLayer) -> None:
        next_layer.layer = child_layer(next_layer.context)

    return reply(*args, side_effect=set_layer, **kwargs)
