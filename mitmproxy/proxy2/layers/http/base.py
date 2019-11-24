import abc
import typing

from mitmproxy.proxy2 import commands, events

StreamId = int


class HttpEvent(events.Event):
    stream_id: StreamId

    # we need stream ids on every event to avoid race conditions

    def __init__(self, stream_id: StreamId):
        self.stream_id = stream_id

    def __repr__(self) -> str:
        x = self.__dict__.copy()
        x.pop("stream_id")
        return f"{type(self).__name__}({repr(x) if x else ''})"


class HttpConnection(abc.ABC):
    @abc.abstractmethod
    def handle_event(self, event: events.Event) -> typing.Iterator[HttpEvent]:
        yield from ()

    @abc.abstractmethod
    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        yield from ()


__all__ = [
    "HttpConnection",
    "StreamId",
    "HttpEvent",
]
