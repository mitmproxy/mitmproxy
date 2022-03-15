import asyncio

from mitmproxy.test.taddons import RecordingMaster


async def err():
    raise RuntimeError


async def test_exception_handler():
    m = RecordingMaster(None)
    running = asyncio.create_task(m.run())
    asyncio.create_task(err())
    await m.await_log("Traceback", level="error")
    m.shutdown()
    await running
