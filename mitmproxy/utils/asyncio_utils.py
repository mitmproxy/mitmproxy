import asyncio
import os
import sys
import time
from collections.abc import Coroutine
from collections.abc import Iterator
from contextlib import contextmanager

from mitmproxy.utils import human


def create_task(
    coro: Coroutine,
    *,
    name: str,
    client: tuple | None = None,
) -> asyncio.Task:
    """
    Like asyncio.create_task, but also store some debug info on the task object.
    """
    t = asyncio.create_task(coro)
    set_task_debug_info(t, name=name, client=client)
    return t


def set_task_debug_info(
    task: asyncio.Task,
    *,
    name: str,
    client: tuple | None = None,
) -> None:
    """Set debug info for an externally-spawned task."""
    task.created = time.time()  # type: ignore
    if __debug__ is True and (test := os.environ.get("PYTEST_CURRENT_TEST", None)):
        name = f"{name} [created in {test}]"
    task.set_name(name)
    if client:
        task.client = client  # type: ignore


def set_current_task_debug_info(
    *,
    name: str,
    client: tuple | None = None,
) -> None:
    """Set debug info for the current task."""
    task = asyncio.current_task()
    assert task
    set_task_debug_info(task, name=name, client=client)


def task_repr(task: asyncio.Task) -> str:
    """Get a task representation with debug info."""
    name = task.get_name()
    a: float = getattr(task, "created", 0)
    if a:
        age = f" (age: {time.time() - a:.0f}s)"
    else:
        age = ""
    client = getattr(task, "client", "")
    if client:
        client = f"{human.format_address(client)}: "
    return f"{client}{name}{age}"


@contextmanager
def install_exception_handler(handler) -> Iterator[None]:
    loop = asyncio.get_running_loop()
    existing = loop.get_exception_handler()
    loop.set_exception_handler(handler)
    try:
        yield
    finally:
        loop.set_exception_handler(existing)


@contextmanager
def set_eager_task_factory() -> Iterator[None]:
    loop = asyncio.get_running_loop()
    if sys.version_info < (3, 12):  # pragma: no cover
        yield
    else:
        existing = loop.get_task_factory()
        loop.set_task_factory(asyncio.eager_task_factory)  # type: ignore
        try:
            yield
        finally:
            loop.set_task_factory(existing)
