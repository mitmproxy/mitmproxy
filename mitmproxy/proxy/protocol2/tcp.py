import functools

from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import ClientServerContext
from mitmproxy.proxy.protocol2.events import TEventGenerator
from mitmproxy.proxy.protocol2.layer import Layer

"""
Utility decorators that help build state machines
"""


def defer(event_type):
    """
    Queue up the events matching the specified event type and emit them immediately
    after the state has changed.
    """

    def decorator(f):
        deferred = []

        @functools.wraps(f)
        def wrapper(self, event: events.Event):
            if isinstance(event, event_type):
                deferred.append(event)
            else:
                yield from f(self, event)
                if self.state != f:
                    for event in deferred:
                        yield from self.state(event)
                    deferred.clear()

        return wrapper

    return decorator


def exit_on_close(f):
    """
    Stop all further interaction once a single close event has been observed.
    """
    closed = False

    @functools.wraps(f)
    def wrapper(self, event: events.Event):
        nonlocal closed
        if isinstance(event, events.CloseConnection):
            closed = True
        if not closed:
            yield from f(self, event)

    return wrapper


class TCPLayer(Layer):
    context = None  # type: ClientServerContext

    def __init__(self, context: ClientServerContext):
        super().__init__(context)
        self.state = self.start

    def handle_event(self, event: events.Event) -> TEventGenerator:
        yield from self.state(event)

    def start(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.OpenConnection):
            if not self.context.server.connected:
                yield events.OpenConnection(self.context.server)
                self.state = self.wait_for_open
            else:
                self.state = self.relay_messages
        else:
            raise TypeError("Unexpected event: {}".format(event))

    @defer(events.ReceiveData)
    @exit_on_close
    def wait_for_open(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.OpenConnection):
            # connection is now open
            self.state = self.relay_messages
        else:
            raise TypeError("Unexpected event: {}".format(event))
            # noinspection PyUnreachableCode
            yield

    def relay_messages(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.ReceiveData):
            if event.connection == self.context.client:
                dst = self.context.server
            else:
                dst = self.context.client
            yield events.SendData(dst, event.data)
        if isinstance(event, events.CloseConnection):
            pass  # TODO: close other connection here.
        else:
            raise TypeError("Unexpected event: {}".format(event))
