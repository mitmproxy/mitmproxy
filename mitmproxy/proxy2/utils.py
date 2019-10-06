"""
Utility decorators that help build state machines
"""
import functools
from typing import Optional, List

from mitmproxy.proxy2 import events


class Buffer:
    """Adapted from h11"""
    def __init__(self):
        self._data = bytearray()
        self._looked_until = 0
        self._looked_for = b""

    def __bool__(self):
        return bool(len(self))

    def __bytes__(self):
        return bytes(self._data)

    def __len__(self):
        return len(self._data)

    def __iadd__(self, data: bytes) -> "Buffer":
        self._data += data
        return self

    def extract_at_most(self, count: int) -> bytes:
        out = self._data[:count]
        self._data = self._data[count:]
        self._looked_until -= len(out)
        return out

    def extract_until_next(self, needle: bytes) -> Optional[bytes]:
        # Returns extracted bytes on success (advancing offset), or None on
        # failure
        if self._looked_for == needle:
            search_start = max(0, self._looked_until - len(needle) + 1)
        else:
            search_start = 0
        offset = self._data.find(needle, search_start)
        if offset == -1:
            self._looked_until = len(self._data)
            self._looked_for = needle
            return None
        else:
            return self.extract_at_most(offset + len(needle))

    # HTTP/1.1 has a number of constructs where you keep reading lines until
    # you see a blank one. This does that, and then returns the lines.
    def extract_lines(self) -> Optional[List[bytes]]:
        if self._data[:2] == b"\r\n":
            self.extract_at_most(2)
            return []
        else:
            data = self.extract_until_next(b"\r\n\r\n")
            if data is None:
                return None
            lines = data.split(b"\r\n")
            assert lines[-2] == lines[-1] == b""
            del lines[-2:]
            return lines



def expect(*event_types):
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
                raise TypeError(
                    "Invalid event type at {}: Expected {}, got {}.".format(f, event_types, event)
                )

        return wrapper

    return decorator


# not used at the moment. We may not need this at all if the blocking yield continues to work as expected.
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


# not used at the moment.
def exit_on_close(f):
    """
    Stop all further interaction once a single close event has been observed.
    """
    closed = False

    @functools.wraps(f)
    def wrapper(self, event: events.Event):
        nonlocal closed
        if isinstance(event, events.ConnectionClosed):
            closed = True
        if not closed:
            yield from f(self, event)

    return wrapper
