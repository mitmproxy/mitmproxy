import asyncio
import gc

from mitmproxy.master import Master


async def err():
    raise RuntimeError


async def test_exception_handler(caplog_async):
    caplog_async.set_level("ERROR")

    # start proxy master and let it initialize its exception handler
    master = Master(None)
    running = asyncio.create_task(master.run())
    await asyncio.sleep(0)

    # create a task with an unhandled exception...
    task = asyncio.create_task(err())
    # make sure said task is run...
    await asyncio.sleep(0)

    # and garbage-collected...
    assert task
    del task
    gc.collect()

    # and ensure that this triggered a log entry.
    await caplog_async.await_log("Traceback")

    master.shutdown()
    await running
