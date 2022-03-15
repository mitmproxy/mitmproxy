import asyncio
import concurrent.futures
import signal
import sys
import time
from asyncio import tasks
from collections.abc import Coroutine
from typing import Awaitable, Callable, Optional, TypeVar

from mitmproxy.utils import human


def cancel_task(task: asyncio.Task, message: str) -> None:
    """Like task.cancel(), but optionally with a message if the Python version supports it."""
    if sys.version_info >= (3, 9):
        task.cancel(message)  # type: ignore
    else:  # pragma: no cover
        task.cancel()


def create_task(
    coro: Coroutine, *,
    name: str,
    client: Optional[tuple] = None,
    ignore_closed_loop: bool = True,
) -> Optional[asyncio.Task]:
    """
    Like asyncio.create_task, but also store some debug info on the task object.

    If ignore_closed_loop is True, the task will be silently discarded if the event loop is closed.
    This is currently useful during shutdown where no new tasks can be spawned.
    Ideally we stop closing the event loop during shutdown and then remove this parameter.
    """
    try:
        t = asyncio.create_task(coro, name=name)
    except RuntimeError:
        if ignore_closed_loop:
            coro.close()
            return None
        else:
            raise
    set_task_debug_info(t, name=name, client=client)
    return t


def set_task_debug_info(
    task: asyncio.Task,
    *,
    name: str,
    client: Optional[tuple] = None,
) -> None:
    """Set debug info for an externally-spawned task."""
    task.created = time.time()  # type: ignore
    task.set_name(name)
    if client:
        task.client = client  # type: ignore


def task_repr(task: asyncio.Task) -> str:
    """Get a task representation with debug info."""
    name = task.get_name()
    age = getattr(task, "created", "")
    if age:
        age = f" (age: {time.time() - age:.0f}s)"
    client = getattr(task, "client", "")
    if client:
        client = f"{human.format_address(client)}: "
    return f"{client}{name}{age}"


T = TypeVar("T")


def run(
    main_func: Awaitable[T],
    ctrl_c_handler: Callable,
    sigterm_handler: Callable,
) -> T:
    """
    Like `asyncio.run`, but with cross-platform Ctrl+C support.

    The main problem with Ctrl+C is that it raises a KeyboardInterrupt on Windows,
    which terminates the current event loop. This method here moves the event loop to a second thread,
    gracefully catches KeyboardInterrupt in the main thread, and then calls the sigint handler.
    """

    loop = asyncio.new_event_loop()

    try:
        loop.add_signal_handler(signal.SIGINT, ctrl_c_handler)
        loop.add_signal_handler(signal.SIGTERM, sigterm_handler)
        return _run_loop(loop, main_func)
    except NotImplementedError:
        pass

    # Windows code path. We don't make this path of the except clause above
    # because that creates "during the handling of another exception" messages
    with concurrent.futures.ThreadPoolExecutor(thread_name_prefix="eventloop") as executor:
        future = executor.submit(_run_loop, loop, main_func)

        while True:
            try:
                # A larger timeout doesn't work, KeyboardInterrupt is not detected then.
                return future.result(.1)
            except concurrent.futures.TimeoutError:
                pass
            except KeyboardInterrupt:
                loop.call_soon_threadsafe(ctrl_c_handler)


def _run_loop(loop: asyncio.AbstractEventLoop, main_func: Awaitable[T]) -> T:
    # this method mimics what `asyncio.run` is doing.
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(main_func)
    finally:
        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.set_event_loop(None)
            loop.close()


# copied from https://github.com/python/cpython/blob/3.10/Lib/asyncio/runners.py
def _cancel_all_tasks(loop):
    to_cancel = tasks.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(tasks.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'unhandled exception during asyncio.run() shutdown',
                'exception': task.exception(),
                'task': task,
            })


if __name__ == "__main__":
    done = asyncio.Event()


    async def main():
        while True:
            print("...")
            try:
                await asyncio.wait_for(done.wait(), 1)
                break
            except asyncio.TimeoutError:
                pass
        return 42


    print(f"{run(main(), done.set, done.set)=}")


    async def main_err():
        raise RuntimeError


    try:
        run(main_err(), lambda: 0, lambda: 0)
    except RuntimeError:
        print("error propagation ok.")
