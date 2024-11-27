"""
This module provides signals, which are a simple dispatching system that allows any number of interested parties
to subscribe to events ("signals").

This is similar to the Blinker library (https://pypi.org/project/blinker/), with the following changes:
  - provides only a small subset of Blinker's functionality
  - supports type hints
  - supports async receivers.
"""

from __future__ import annotations

import asyncio
import inspect
import weakref
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import cast
from typing import Generic
from typing import ParamSpec
from typing import TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def make_weak_ref(obj: Any) -> weakref.ReferenceType:
    """
    Like weakref.ref(), but using weakref.WeakMethod for bound methods.
    """
    if hasattr(obj, "__self__"):
        return cast(weakref.ref, weakref.WeakMethod(obj))
    else:
        return weakref.ref(obj)


# We're running into https://github.com/python/mypy/issues/6073 here,
# which is why the base class is a mixin and not a generic superclass.
class _SignalMixin:
    def __init__(self) -> None:
        self.receivers: list[weakref.ref[Callable]] = []

    def connect(self, receiver: Callable) -> None:
        """
        Register a signal receiver.

        The signal will only hold a weak reference to the receiver function.
        """
        receiver = make_weak_ref(receiver)
        self.receivers.append(receiver)

    def disconnect(self, receiver: Callable) -> None:
        self.receivers = [r for r in self.receivers if r() != receiver]

    def notify(self, *args, **kwargs):
        cleanup = False
        for ref in self.receivers:
            r = ref()
            if r is not None:
                yield r(*args, **kwargs)
            else:
                cleanup = True
        if cleanup:
            self.receivers = [r for r in self.receivers if r() is not None]


class _SyncSignal(Generic[P], _SignalMixin):
    def connect(self, receiver: Callable[P, None]) -> None:
        assert not asyncio.iscoroutinefunction(receiver)
        super().connect(receiver)

    def disconnect(self, receiver: Callable[P, None]) -> None:
        super().disconnect(receiver)

    def send(self, *args: P.args, **kwargs: P.kwargs) -> None:
        for ret in super().notify(*args, **kwargs):
            assert ret is None or not inspect.isawaitable(ret)


class _AsyncSignal(Generic[P], _SignalMixin):
    def connect(self, receiver: Callable[P, Awaitable[None] | None]) -> None:
        super().connect(receiver)

    def disconnect(self, receiver: Callable[P, Awaitable[None] | None]) -> None:
        super().disconnect(receiver)

    async def send(self, *args: P.args, **kwargs: P.kwargs) -> None:
        await asyncio.gather(
            *[
                aws
                for aws in super().notify(*args, **kwargs)
                if aws is not None and inspect.isawaitable(aws)
            ]
        )


# noinspection PyPep8Naming
def SyncSignal(receiver_spec: Callable[P, None]) -> _SyncSignal[P]:
    """
    Create a synchronous signal with the given function signature for receivers.

    Example:

        s = SyncSignal(lambda event: None)  # all receivers must accept a single "event" argument.
        def receiver(event):
            print(event)

        s.connect(receiver)
        s.send("foo")  # prints foo
        s.send(event="bar")  # prints bar

        def receiver2():
            ...

        s.connect(receiver2)  # mypy complains about receiver2 not having the right signature

        s2 = SyncSignal(lambda: None)  # this signal has no arguments
        s2.send()
    """
    return cast(_SyncSignal[P], _SyncSignal())


# noinspection PyPep8Naming
def AsyncSignal(receiver_spec: Callable[P, Awaitable[None] | None]) -> _AsyncSignal[P]:
    """
    Create an signal that supports both regular and async receivers:

    Example:

        s = AsyncSignal(lambda event: None)
        async def receiver(event):
            print(event)
        s.connect(receiver)
        await s.send("foo")  # prints foo
    """
    return cast(_AsyncSignal[P], _AsyncSignal())
