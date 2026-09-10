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


async def test_running_warns_for_unknown_option(caplog_async):
    caplog_async.set_level("WARNING")

    master = Master(None)
    master.options.set("somebadname=value", defer=True)

    await master.running()

    assert "Unknown option(s): somebadname" in caplog_async.caplog.text


async def test_running_does_not_warn_for_known_option(caplog_async):
    caplog_async.set_level("WARNING")

    master = Master(None)
    master.options.set("server=false", defer=True)

    assert not master.options.deferred

    await master.running()

    assert "Unknown option(s):" not in caplog_async.caplog.text
