import asyncio

from mitmproxy.master import Master


async def err():
    raise RuntimeError


async def test_exception_handler(caplog):
    m = Master(None)
    running = asyncio.create_task(m.run())
    asyncio.create_task(err())
    await asyncio.sleep(0)
    assert "Traceback" in caplog.text
    m.shutdown()
    await running
