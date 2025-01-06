import asyncio
import gc
import sys

import pytest

from mitmproxy.utils import asyncio_utils


async def ttask():
    await asyncio.sleep(0)
    asyncio_utils.set_current_task_debug_info(name="newname")
    await asyncio.sleep(999)


async def test_simple(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo")
    task = asyncio_utils.create_task(
        ttask(), name="ttask", keep_ref=True, client=("127.0.0.1", 42313)
    )
    assert (
        asyncio_utils.task_repr(task)
        == "127.0.0.1:42313: ttask [created in test_foo] (age: 0s)"
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert "newname" in asyncio_utils.task_repr(task)
    delattr(task, "created")
    assert asyncio_utils.task_repr(task)


async def _raise():
    raise RuntimeError()


async def test_install_exception_handler():
    e = asyncio.Event()
    with asyncio_utils.install_exception_handler(lambda *_, **__: e.set()):
        t = asyncio.create_task(_raise())
        await asyncio.sleep(0)
        assert t.done()
        del t
        gc.collect()
        await e.wait()


async def test_eager_task_factory():
    x = False

    async def task():
        nonlocal x
        x = True

    # assert that override works...
    assert type(asyncio.get_event_loop_policy()) is asyncio.DefaultEventLoopPolicy

    with asyncio_utils.set_eager_task_factory():
        _ = asyncio.create_task(task())
        if sys.version_info >= (3, 12):
            # ...and the context manager is effective
            assert x


@pytest.fixture()
def event_loop_policy(request):
    # override EagerTaskCreationEventLoopPolicy from top-level conftest
    return asyncio.DefaultEventLoopPolicy()
