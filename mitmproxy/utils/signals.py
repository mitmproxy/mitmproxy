import inspect
from typing import Any, Callable, TypeVar
import blinker

from mitmproxy import ctx, exceptions


# NOTE:
# Once we drop support for Python 3.9, we should consider something like:
#
# P = ParamSpec("P")
# R = TypeVar("R")
#
# class SyncSignal(Generic[P, R]):
#     def connect(self, receiver: Callable[Concatenate[Any, P], R]) -> Callable[Concatenate[Any, P], R]:
#         ...
#
#     def send(self, sender: Any, *args: P.args, **kwargs: P.kwargs) -> list[tuple[Callable[Concatenate[Any, P], R], R]]:
#         ...
#
# Alternatively, once PEP 692 lands, we could make kwargs type-safe and use event args TypedDicts.


T = TypeVar("T", bound=Callable)


class SyncSignal(blinker.Signal):
    def connect(self, receiver: T, sender: Any = blinker.ANY, weak: bool = True) -> T:
        if inspect.iscoroutinefunction(receiver):
            raise exceptions.TypeError(
                f"Receiver {receiver} for {self} cannot be an asynchronous function."
            )
        return super().connect(receiver, sender, weak)

    def send(self, *sender, **kwargs) -> list[tuple[Any, Any]]:
        sent = super().send(*sender, **kwargs)
        for receiver, ret in sent:
            if ret is not None and inspect.isawaitable(ret):
                ctx.log.warn(
                    f"Receiver {receiver} for {self} returned awaitable {ret}."
                )
        return sent


class AsyncSignal(blinker.Signal):
    def connect(self, receiver: T, sender: Any = blinker.ANY, weak: bool = True) -> T:
        # allow better typing than blinker
        return super().connect(receiver, sender, weak)

    async def send(self, *sender, **kwargs) -> list[tuple[Any, Any]]:
        return [
            (
                receiver,
                await ret if ret is not None and inspect.isawaitable(ret) else ret,
            )
            for receiver, ret in super().send(*sender, **kwargs)
        ]
