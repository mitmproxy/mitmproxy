"""
Base class for protocol layers.
"""
import collections
import textwrap
import typing
from abc import abstractmethod

from mitmproxy import log
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.commands import Hook
from mitmproxy.proxy2.context import Connection, Context


class Paused(typing.NamedTuple):
    """
    State of a layer that's paused because it is waiting for a command reply.
    """
    command: commands.Command
    generator: commands.TCommandGenerator


class Layer:
    __last_debug_message: typing.ClassVar[str] = ""
    context: Context
    _paused: typing.Optional[Paused]
    _paused_event_queue: typing.Deque[events.Event]
    debug: typing.Optional[str] = None
    """
    Enable debug logging by assigning a prefix string for log messages.
    Different amounts of whitespace for different layers work well.
    """

    def __init__(self, context: Context) -> None:
        self.context = context
        self.context.layers.append(self)
        self._paused = None
        self._paused_event_queue = collections.deque()

        show_debug_output = (
                "termlog_verbosity" in context.options and
                log.log_tier(context.options.termlog_verbosity) >= log.log_tier("debug")
        )
        if show_debug_output:
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
        if Layer.__last_debug_message == message:
            message = message.split("\n", 1)[0].strip()
        else:
            Layer.__last_debug_message = message
        return commands.Log(
            textwrap.indent(message, self.debug),
            "debug"
        )

    @abstractmethod
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        """Handle a proxy server event"""
        yield from ()  # pragma: no cover

    def handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if self._paused:
            # did we just receive the reply we were waiting for?
            pause_finished = (
                    isinstance(event, events.CommandReply) and
                    event.command is self._paused.command
            )
            if self.debug is not None:
                yield self.__debug(f"{'>>' if pause_finished else '>!'} {event}")
            if pause_finished:
                yield from self.__continue(event)
            else:
                self._paused_event_queue.append(event)
        else:
            if self.debug is not None:
                yield self.__debug(f">> {event}")
            command_generator = self._handle_event(event)
            yield from self.__process(command_generator)

    def __process(self, command_generator: commands.TCommandGenerator, send=None):
        """
        yield all commands from a generator.
        if a command is blocking, the layer is paused and this function returns before
        processing any other commands.
        """
        try:
            command = command_generator.send(send)
        except StopIteration:
            return

        while command:
            if self.debug is not None:
                if not isinstance(command, commands.Log):
                    yield self.__debug(f"<< {command}")
            if command.blocking is True:
                command.blocking = self  # assign to our layer so that higher layers don't block.
                self._paused = Paused(
                    command,
                    command_generator,
                )
                yield command
                return
            else:
                yield command
                command = next(command_generator, None)

    def __continue(self, event: events.CommandReply):
        """continue processing events after being paused"""
        command_generator = self._paused.generator
        self._paused = None
        yield from self.__process(command_generator, event.reply)

        while not self._paused and self._paused_event_queue:
            event = self._paused_event_queue.popleft()
            if self.debug is not None:
                yield self.__debug(f"!> {event}")
            command_generator = self._handle_event(event)
            yield from self.__process(command_generator)


mevents = events  # alias here because autocomplete above should not have aliased version.


class NextLayerHook(Hook):
    data: "NextLayer"


class NextLayer(Layer):
    layer: typing.Optional[Layer]
    """The next layer. To be set by an addon."""

    events: typing.List[mevents.Event]
    """All events that happened before a decision was made."""

    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.context.layers.remove(self)
        self.events = []
        self.layer = None
        self._handle = None

    def __repr__(self):
        return f"NextLayer:{repr(self.layer)}"

    def handle_event(self, event: mevents.Event):
        if self._handle is not None:
            yield from self._handle(event)
        else:
            yield from super().handle_event(event)

    def _handle_event(self, event: mevents.Event):
        self.events.append(event)

        # We receive new data. Let's find out if we can determine the next layer now?
        if isinstance(event, mevents.DataReceived):
            # For now, we only ask if we have received new data to reduce hook noise.
            yield from self.ask_now()

    def ask_now(self):
        """
        Manually trigger a next_layer hook.
        The only use at the moment is to make sure that the top layer is initialized.
        """
        yield NextLayerHook(self)

        # Has an addon decided on the next layer yet?
        if self.layer:
            for e in self.events:
                yield from self.layer.handle_event(e)
            self.events.clear()

            # Why do we need three assignments here?
            #  1. When this function here is invoked we may have paused events. Those should be
            #     forwarded to the sublayer right away, so we reassign ._handle_event.
            #  2. This layer is not needed anymore, so we directly reassign .handle_event.
            #  3. Some layers may however still have a reference to the old .handle_event.
            #     ._handle is just an optimization to reduce the callstack in these cases.
            self.handle_event = self.layer.handle_event
            self._handle_event = self.layer._handle_event
            self._handle = self.layer.handle_event

    # Utility methods for whoever decides what the next layer is going to be.
    def data_client(self):
        return self._data(self.context.client)

    def data_server(self):
        return self._data(self.context.server)

    def _data(self, connection: Connection):
        data = (
            e.data for e in self.events
            if isinstance(e, mevents.DataReceived) and e.connection == connection
        )
        return b"".join(data)
