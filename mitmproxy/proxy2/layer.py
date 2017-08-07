"""
Base class for protocol layers.
"""
import collections
import typing
from abc import abstractmethod

from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Context, Connection


class Paused(typing.NamedTuple):
    """
    State of a layer that's paused because it is waiting for a command reply.
    """
    command: commands.Command
    generator: commands.TCommandGenerator


class Layer:
    context: Context
    _paused: typing.Optional[Paused]

    def __init__(self, context: Context) -> None:
        self.context = context
        self.context.layers.append(self)
        self._paused = None
        self._paused_event_queue: typing.Deque[events.Event] = collections.deque()

    def _debug(self, *args):
        pass  # print(*args)

    @abstractmethod
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        """Handle a proxy server event"""
        if False:
            yield None

    def handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if self._paused:
            # did we just receive the reply we were waiting for?
            pause_finished = (
                isinstance(event, events.CommandReply) and
                event.command is self._paused.command
            )
            if pause_finished:
                yield from self.__continue(event)
            else:
                self._paused_event_queue.append(event)
                self._debug("Paused Event Queue: " + repr(self._paused_event_queue))
        else:
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
            if command.blocking is True:
                self._debug("start pausing")
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
        self._debug("continue")
        command_generator = self._paused.generator
        self._paused = None
        yield from self.__process(command_generator, event.reply)

        while not self._paused and self._paused_event_queue:
            event = self._paused_event_queue.popleft()
            self._debug(f"<# Paused event: {event}")
            command_generator = self._handle_event(event)
            yield from self.__process(command_generator)
            self._debug("#>")


mevents = events  # alias here because autocomplete above should not have aliased version.


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

    def __repr__(self):
        return f"NextLayer:{repr(self.layer)}"

    def _handle_event(self, event: mevents.Event):
        self.events.append(event)

        if not isinstance(event, mevents.DataReceived):
            # We only ask if we have received new data.
            return

        yield commands.Hook("next_layer", self)

        # Has an addon decided on the next layer yet?
        if self.layer:
            for e in self.events:
                yield from self.layer.handle_event(e)
            self.events.clear()

            self._handle_event = self.layer.handle_event

    # Utility methods for addon.

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
