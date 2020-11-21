import asyncio
import sys
import time
from collections.abc import Coroutine
from typing import Optional

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
