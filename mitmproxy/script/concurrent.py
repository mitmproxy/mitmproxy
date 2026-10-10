"""Primitives for running callbacks outside the main event-loop thread."""

import asyncio
import inspect
from collections.abc import AsyncGenerator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from functools import wraps
from typing import cast
from typing import overload
from typing import ParamSpec
from typing import TypeVar

from mitmproxy import hooks

P = ParamSpec("P")
T = TypeVar("T")


@overload
def run_in_thread(  # type: ignore[overload-overlap]
    function: Callable[P, Generator[T, None, None]],
) -> Callable[P, AsyncGenerator[T, None]]: ...


@overload
def run_in_thread(function: Callable[P, T]) -> Callable[P, Awaitable[T]]: ...


def run_in_thread(
    function: Callable[P, Generator[T, None, None]] | Callable[P, T],
) -> Callable[P, AsyncGenerator[T, None]] | Callable[P, Awaitable[T]]:
    """Run a synchronous function or generator function in worker threads."""
    if inspect.iscoroutinefunction(function) or inspect.isasyncgenfunction(function):
        raise ValueError("run_in_thread cannot be used with async functions.")

    if inspect.isgeneratorfunction(function):
        generator_function = cast(Callable[P, Generator[T, None, None]], function)

        @wraps(function)
        async def generator_wrapper(
            *args: P.args, **kwargs: P.kwargs
        ) -> AsyncGenerator[T, None]:
            iterator = generator_function(*args, **kwargs)

            # StopIteration can't be raised in an async generator,
            # so we use a sentinel value to signal the end of the iterator.
            class Done:
                __slots__ = ()

            done = Done()

            while True:
                item = await asyncio.to_thread(next, iterator, done)
                if isinstance(item, Done):
                    break
                yield item

        return generator_wrapper

    sync_function = cast(Callable[P, T], function)

    @wraps(function)
    async def function_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(sync_function, *args, **kwargs)

    return function_wrapper


def concurrent(fn):
    if fn.__name__ not in set(hooks.all_hooks.keys()) - {"load", "configure"}:
        raise NotImplementedError(
            "Concurrent decorator not supported for '%s' method." % fn.__name__
        )

    async def _concurrent(*args):
        def run():
            if inspect.iscoroutinefunction(fn):
                # Run the async function in a new event loop
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(fn(*args))
                finally:
                    loop.close()
            else:
                fn(*args)

        await asyncio.get_running_loop().run_in_executor(None, run)

    return _concurrent
