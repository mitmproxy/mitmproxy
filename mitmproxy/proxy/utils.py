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
                    event_types_str = '|'.join(e.__name__ for e in event_types) or "no events"
                    raise AssertionError(
                        f"Unexpected event type at {f.__qualname__}: "
                        f"Expected {event_types_str}, got {event}."
                    )

            return _check_event_type
        else:  # pragma: no cover
            return f

    return decorator
