import asyncio

from mitmproxy.utils import asyncio_utils


async def ttask():
    asyncio_utils.set_current_task_debug_info(name="newname")
    await asyncio.sleep(999)


async def test_simple():
    task = asyncio_utils.create_task(ttask(), name="ttask", client=("127.0.0.1", 42313))
    assert asyncio_utils.task_repr(task) == "127.0.0.1:42313: ttask (age: 0s)"
    await asyncio.sleep(0)
    assert "newname" in asyncio_utils.task_repr(task)
    delattr(task, "created")
    assert asyncio_utils.task_repr(task)
