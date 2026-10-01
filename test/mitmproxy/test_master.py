import asyncio
import gc
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.master import Master
from mitmproxy.proxy.mode_servers import LocalRedirectorInstance


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


@pytest.mark.parametrize("during_startup", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
async def test_local_redirector_shutdown(monkeypatch, during_startup, cancel):
    server = Mock()
    waiting = asyncio.Event()
    closed = asyncio.Event()

    async def wait_closed():
        waiting.set()
        await closed.wait()

    server.wait_closed = AsyncMock(side_effect=wait_closed)
    monkeypatch.setattr(LocalRedirectorInstance, "_server", server)
    monkeypatch.setattr(LocalRedirectorInstance, "_instance", None)
    master = Master(None)
    proxyserver = Proxyserver()
    master.addons.add(proxyserver)
    entered = asyncio.Event()
    setup_finished = asyncio.Event()

    async def setup_servers():
        try:
            if during_startup:
                entered.set()
                await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            setup_finished.set()

    async def running():
        entered.set()
        proxyserver.running()

    monkeypatch.setattr(proxyserver, "setup_servers", setup_servers)
    monkeypatch.setattr(master, "running", running)
    task = asyncio.create_task(master.run())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        if cancel:
            task.cancel()
        else:
            master.shutdown()
        await asyncio.wait_for(waiting.wait(), 1)
        assert setup_finished.is_set()
        server.close.assert_called_once()
        assert not task.done()
        closed.set()
        if cancel:
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            await task
        assert LocalRedirectorInstance._server is None
        assert not proxyserver.is_running
    finally:
        closed.set()
        master.shutdown()
        await asyncio.gather(task, return_exceptions=True)
