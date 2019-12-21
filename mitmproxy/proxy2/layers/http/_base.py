import abc
import typing
from dataclasses import dataclass

from mitmproxy.proxy2 import events, layer

StreamId = int


@dataclass
class HttpEvent(events.Event):
    # we need stream ids on every event to avoid race conditions
    stream_id: StreamId

    def __repr__(self) -> str:
        x = self.__dict__.copy()
        x.pop("stream_id")
        return f"{type(self).__name__}({repr(x) if x else ''})"


class HttpConnection(abc.ABC):
    @abc.abstractmethod
    def handle_event(self, event: events.Event) -> typing.Iterator[HttpEvent]:
        yield from ()

    @abc.abstractmethod
    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        yield from ()


__all__ = [
    "HttpConnection",
    "StreamId",
    "HttpEvent",
]
