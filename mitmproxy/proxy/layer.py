"""
Base class for protocol layers.
"""

import collections
import textwrap
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from dataclasses import dataclass
from logging import DEBUG
from typing import Any
from typing import ClassVar
from typing import NamedTuple
from typing import TypeVar

from mitmproxy.connection import Connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy.commands import Command
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.context import Context

T = TypeVar("T")
CommandGenerator = Generator[Command, Any, T]
"""
A function annotated with CommandGenerator[bool] may yield commands and ultimately return a boolean value.
"""


MAX_LOG_STATEMENT_SIZE = 2048
"""Maximum size of individual log statements before they will be truncated."""


class Paused(NamedTuple):
    """
    State of a layer that's paused because it is waiting for a command reply.
    """

    command: commands.Command
    generator: CommandGenerator


class Layer:
    """
    The base class for all protocol layers.

    Layers interface with their child layer(s) by calling .handle_event(event),
    which returns a list (more precisely: a generator) of commands.
    Most layers do not implement .directly, but instead implement ._handle_event, which
    is called by the default implementation of .handle_event.
    The default implementation of .handle_event allows layers to emulate blocking code:
    When ._handle_event yields a command that has its blocking attribute set to True, .handle_event pauses
    the execution of ._handle_event and waits until it is called with the corresponding CommandCompleted event.
    All events encountered in the meantime are buffered and replayed after execution is resumed.

    The result is code that looks like blocking code, but is not blocking:

        def _handle_event(self, event):
            err = yield OpenConnection(server)  # execution continues here after a connection has been established.

    Technically this is very similar to how coroutines are implemented.
    """

    __last_debug_message: ClassVar[str] = ""
    context: Context
    _paused: Paused | None
    """
    If execution is currently paused, this attribute stores the paused coroutine
    and the command for which we are expecting a reply.
    """
    _paused_event_queue: collections.deque[events.Event]
    """
    All events that have occurred since execution was paused.
    These will be replayed to ._child_layer once we resume.
    """
    debug: str | None = None
    """
    Enable debug logging by assigning a prefix string for log messages.
    Different amounts of whitespace for different layers work well.
    """

    def __init__(self, context: Context) -> None:
        self.context = context
        self.context.layers.append(self)
        self._paused = None
        self._paused_event_queue = collections.deque()

        show_debug_output = getattr(context.options, "proxy_debug", False)
        if show_debug_output:  # pragma: no cover
            self.debug = "  " * len(context.layers)

    def __repr__(self):
        statefun = getattr(self, "state", self._handle_event)
        state = getattr(statefun, "__name__", "")
        state = state.replace("state_", "")
        if state == "_handle_event":
            state = ""
        else:
            state = f"state: {state}"
        return f"{type(self).__name__}({state})"

    def __debug(self, message):
        """yield a Log command indicating what message is passing through this layer."""
        if len(message) > MAX_LOG_STATEMENT_SIZE:
            message = message[:MAX_LOG_STATEMENT_SIZE] + "…"
        if Layer.__last_debug_message == message:
            message = message.split("\n", 1)[0].strip()
            if len(message) > 256:
                message = message[:256] + "…"
        else:
            Layer.__last_debug_message = message
        assert self.debug is not None
        return commands.Log(textwrap.indent(message, self.debug), DEBUG)

    @property
    def stack_pos(self) -> str:
        """repr() for this layer and all its parent layers, only useful for debugging."""
        try:
            idx = self.context.layers.index(self)
        except ValueError:
            return repr(self)
        else:
            return " >> ".join(repr(x) for x in self.context.layers[: idx + 1])

    @abstractmethod
    def _handle_event(self, event: events.Event) -> CommandGenerator[None]:
        """Handle a proxy server event"""
        yield from ()  # pragma: no cover

    def handle_event(self, event: events.Event) -> CommandGenerator[None]:
        if self._paused:
            # did we just receive the reply we were waiting for?
            pause_finished = (
                isinstance(event, events.CommandCompleted)
                and event.command is self._paused.command
            )
            if self.debug is not None:
                yield self.__debug(f"{'>>' if pause_finished else '>!'} {event}")
            if pause_finished:
                assert isinstance(event, events.CommandCompleted)
                yield from self.__continue(event)
            else:
                self._paused_event_queue.append(event)
        else:
            if self.debug is not None:
                yield self.__debug(f">> {event}")
            command_generator = self._handle_event(event)
            send = None

            # inlined copy of __process to reduce call stack.
            # <✂✂✂>
            try:
                # Run ._handle_event to the next yield statement.
                # If you are not familiar with generators and their .send() method,
                # https://stackoverflow.com/a/12638313/934719 has a good explanation.
                command = command_generator.send(send)
            except StopIteration:
                return

            while True:
                if self.debug is not None:
                    if not isinstance(command, commands.Log):
                        yield self.__debug(f"<< {command}")
                if command.blocking is True:
                    # We only want this layer to block, the outer layers should not block.
                    # For example, take an HTTP/2 connection: If we intercept one particular request,
                    # we don't want all other requests in the connection to be blocked a well.
                    # We signal to outer layers that this command is already handled by assigning our layer to
                    # `.blocking` here (upper layers explicitly check for `is True`).
                    command.blocking = self
                    self._paused = Paused(
                        command,
                        command_generator,
                    )
                    yield command
                    return
                else:
                    yield command
                    try:
                        command = next(command_generator)
                    except StopIteration:
                        return
            # </✂✂✂>

    def __process(self, command_generator: CommandGenerator, send=None):
        """
        Yield commands from a generator.
        If a command is blocking, execution is paused and this function returns without
        processing any further commands.
        """
        try:
            # Run ._handle_event to the next yield statement.
            # If you are not familiar with generators and their .send() method,
            # https://stackoverflow.com/a/12638313/934719 has a good explanation.
            command = command_generator.send(send)
        except StopIteration:
            return

        while True:
            if self.debug is not None:
                if not isinstance(command, commands.Log):
                    yield self.__debug(f"<< {command}")
            if command.blocking is True:
                # We only want this layer to block, the outer layers should not block.
                # For example, take an HTTP/2 connection: If we intercept one particular request,
                # we don't want all other requests in the connection to be blocked a well.
                # We signal to outer layers that this command is already handled by assigning our layer to
                # `.blocking` here (upper layers explicitly check for `is True`).
                command.blocking = self
                self._paused = Paused(
                    command,
                    command_generator,
                )
                yield command
                return
            else:
                yield command
                try:
                    command = next(command_generator)
                except StopIteration:
                    return

    def __continue(self, event: events.CommandCompleted):
        """
        Continue processing events after being paused.
        The tricky part here is that events in the event queue may trigger commands which again pause the execution,
        so we may not be able to process the entire queue.
        """
        assert self._paused is not None
        command_generator = self._paused.generator
        self._paused = None
        yield from self.__process(command_generator, event.reply)

        while not self._paused and self._paused_event_queue:
            ev = self._paused_event_queue.popleft()
            if self.debug is not None:
                yield self.__debug(f"!> {ev}")
            command_generator = self._handle_event(ev)
            yield from self.__process(command_generator)


mevents = (
    events  # alias here because autocomplete above should not have aliased version.
)


class NextLayer(Layer):
    layer: Layer | None
    """The next layer. To be set by an addon."""

    events: list[mevents.Event]
    """All events that happened before a decision was made."""

    _ask_on_start: bool

    def __init__(self, context: Context, ask_on_start: bool = False) -> None:
        super().__init__(context)
        self.context.layers.remove(self)
        self.layer = None
        self.events = []
        self._ask_on_start = ask_on_start
        self._handle: Callable[[mevents.Event], CommandGenerator[None]] | None = None

    def __repr__(self):
        return f"NextLayer:{self.layer!r}"

    def handle_event(self, event: mevents.Event):
        if self._handle is not None:
            yield from self._handle(event)
        else:
            yield from super().handle_event(event)

    def _handle_event(self, event: mevents.Event):
        self.events.append(event)

        # We receive new data. Let's find out if we can determine the next layer now?
        if self._ask_on_start and isinstance(event, events.Start):
            yield from self._ask()
        elif (
            isinstance(event, mevents.ConnectionClosed)
            and event.connection == self.context.client
        ):
            # If we have not determined the next protocol yet and the client already closes the connection,
            # we abort everything.
            yield commands.CloseConnection(self.context.client)
        elif isinstance(event, mevents.DataReceived):
            # For now, we only ask if we have received new data to reduce hook noise.
            yield from self._ask()

    def _ask(self):
        """
        Manually trigger a next_layer hook.
        The only use at the moment is to make sure that the top layer is initialized.
        """
        yield NextLayerHook(self)

        # Has an addon decided on the next layer yet?
        if self.layer:
            if self.debug:
                yield commands.Log(f"{self.debug}[nextlayer] {self.layer!r}", DEBUG)
            for e in self.events:
                yield from self.layer.handle_event(e)
            self.events.clear()

            # Why do we need three assignments here?
            #  1. When this function here is invoked we may have paused events. Those should be
            #     forwarded to the sublayer right away, so we reassign ._handle_event.
            #  2. This layer is not needed anymore, so we directly reassign .handle_event.
            #  3. Some layers may however still have a reference to the old .handle_event.
            #     ._handle is just an optimization to reduce the callstack in these cases.
            self.handle_event = self.layer.handle_event  # type: ignore
            self._handle_event = self.layer.handle_event  # type: ignore
            self._handle = self.layer.handle_event

    # Utility methods for whoever decides what the next layer is going to be.
    def data_client(self):
        return self._data(self.context.client)

    def data_server(self):
        return self._data(self.context.server)

    def _data(self, connection: Connection):
        data = (
            e.data
            for e in self.events
            if isinstance(e, mevents.DataReceived) and e.connection == connection
        )
        return b"".join(data)


@dataclass
class NextLayerHook(StartHook):
    """
    Network layers are being switched. You may change which layer will be used by setting data.layer.

    (by default, this is done by mitmproxy.addons.NextLayer)
    """

    data: NextLayer
