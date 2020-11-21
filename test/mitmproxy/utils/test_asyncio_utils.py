import asyncio
import sys

import pytest

from mitmproxy.utils import asyncio_utils


async def ttask():
    asyncio_utils.set_task_debug_info(
        asyncio.current_task(),
        name="newname",
    )
    await asyncio.sleep(999)


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires Python 3.8")
async def test_simple():
    task = asyncio_utils.create_task(
        ttask(),
        name="ttask",
        client=("127.0.0.1", 42313)
    )
    assert asyncio_utils.task_repr(task) == "127.0.0.1:42313: ttask (age: 0s)"
    await asyncio.sleep(0)
    assert "newname" in asyncio_utils.task_repr(task)
    asyncio_utils.cancel_task(task, "bye")
    await asyncio.sleep(0)
    assert task.cancelled()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires Python 3.8")
def test_closed_loop():
    # Crude test for line coverage.
    # This should eventually go, see the description in asyncio_utils.create_task for details.
    asyncio_utils.create_task(
        ttask(),
        name="ttask",
    )
    with pytest.raises(RuntimeError):
        asyncio_utils.create_task(
            ttask(),
            name="ttask",
            ignore_closed_loop=False,
        )
