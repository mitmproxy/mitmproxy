import asyncio

from mitmproxy.master import Master


async def err():
    raise RuntimeError


class TaskError:
    def running(self):
        # not assigned to anything
        asyncio.create_task(err())


async def test_exception_handler(caplog_async):
    caplog_async.set_level("ERROR")
    m = Master(None)
    m.addons.add(TaskError())
    running = asyncio.create_task(m.run())
    await caplog_async.await_log("Traceback")
    m.shutdown()
    await running
