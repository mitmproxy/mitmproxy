"""
Utility decorators that help build state machines
"""
import functools
from typing import Optional

from mitmproxy.proxy.protocol2 import events


class Buffer:
    def __init__(self):
        self._buffer = bytearray()
        self._eof = False

    def add_data(self, data: bytes) -> None:
        self._buffer.extend(data)

    def add_eof(self):
        if self._eof:
            raise RuntimeError("Unexpected EOF: Already closed.")
        self._eof = True

    def peekexactly(self, n: int) -> Optional[bytes]:
        if not 0 <= n <= len(self._buffer):
            return None
        return bytes(self._buffer[:n])

    def readuntil(self, sep: bytes) -> Optional[bytes]:
        offset = self._buffer.find(sep)
        if offset == -1:
            return None

        return self.readexactly(offset + len(sep))

    def readline(self) -> Optional[bytes]:
        return self.readuntil(b'\n')

    def readexactly(self, n: int) -> Optional[bytes]:
        if not 0 <= n <= len(self._buffer):
            return None
        chunk = self._buffer[:n]
        del self._buffer[:n]
        return bytes(chunk)


def only(*event_types):
    """
    Only allow the given event type.
    If another event is passed, a TypeError is raised.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, event: events.Event):
            if isinstance(event, event_types):
                yield from f(self, event)
            else:
                raise TypeError("Invalid event type: Expected {}, got {}".format(event_types, event))

        return wrapper

    return decorator


def defer(*event_types):
    """
    Queue up the events matching the specified event type and emit them immediately
    after the state has changed.
    """

    def decorator(f):
        deferred = []

        @functools.wraps(f)
        def wrapper(self, event: events.Event):
            if isinstance(event, event_types):
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
