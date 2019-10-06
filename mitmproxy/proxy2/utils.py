"""
Utility decorators that help build state machines
"""
import functools

from mitmproxy.proxy2 import events


def expect(*event_types):
    """
    Only allow the given event type.
    If another event is passed, an AssertionError is raised.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, event: events.Event):
            if isinstance(event, event_types):
                yield from f(self, event)
            else:
                raise AssertionError(f"Unexpected event type at {f}: Expected {event_types}, got {event}.")

        return wrapper

    return decorator
