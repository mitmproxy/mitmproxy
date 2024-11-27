"""
Utility decorators that help build state machines
"""

import functools

from mitmproxy.proxy import events


def expect(*event_types):
    """
    Only allow the given event type.
    If another event is passed, an AssertionError is raised.
    """

    def decorator(f):
        if __debug__ is True:

            @functools.wraps(f)
            def _check_event_type(self, event: events.Event):
                if isinstance(event, event_types):
                    return f(self, event)
                else:
                    event_types_str = (
                        "|".join(e.__name__ for e in event_types) or "no events"
                    )
                    raise AssertionError(
                        f"Unexpected event type at {f.__qualname__}: "
                        f"Expected {event_types_str}, got {event}."
                    )

            return _check_event_type
        else:  # pragma: no cover
            return f

    return decorator


class ReceiveBuffer:
    """
    A data structure to collect stream contents efficiently in O(n).
    """

    _chunks: list[bytes]
    _len: int

    def __init__(self):
        self._chunks = []
        self._len = 0

    def __iadd__(self, other: bytes):
        assert isinstance(other, bytes)
        self._chunks.append(other)
        self._len += len(other)
        return self

    def __len__(self):
        return self._len

    def __bytes__(self):
        return b"".join(self._chunks)

    def __bool__(self):
        return self._len > 0

    def clear(self):
        self._chunks.clear()
        self._len = 0
