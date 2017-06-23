"""
Base class for protocol layers.
"""
import collections
import typing
from abc import ABCMeta, abstractmethod

from mitmproxy.proxy.protocol2 import commands, events
from mitmproxy.proxy.protocol2.context import Context
from mitmproxy.proxy.protocol2.events import Event


class Paused(typing.NamedTuple):
    """
    State of a layer that's paused because it is waiting for a command reply.
    """
    command: commands.Command
    generator: commands.TCommandGenerator


class Layer(metaclass=ABCMeta):
    context: Context
    _paused: typing.Optional[Paused]

    def __init__(self, context: Context) -> None:
        self.context = context
        self._paused = None
        self._paused_event_queue: typing.Deque[events.Event] = collections.deque()

    def _debug(self, x):
        pass # print(x)

    @abstractmethod
    def handle(self, event: Event) -> commands.TCommandGenerator:
        """Handle a proxy server event"""
        if False:
            yield None

    def handle_event(self, event: Event) -> commands.TCommandGenerator:
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
            command_generator = self.handle(event)
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
            command_generator = self.handle(event)
            yield from self.__process(command_generator)
            self._debug("#>")
