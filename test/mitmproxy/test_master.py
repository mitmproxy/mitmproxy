import asyncio
import gc
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from mitmproxy import exceptions
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
@pytest.mark.parametrize("cancel_again", [0, 1, 3])
async def test_local_redirector_shutdown(
    monkeypatch, during_startup, cancel, cancel_again
):
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
    done = AsyncMock(wraps=master.done)
    monkeypatch.setattr(master, "done", done)
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
        for _ in range(cancel_again):
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
        closed.set()
        if cancel or cancel_again:
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            await task
        assert LocalRedirectorInstance._server is None
        assert not proxyserver.is_running
        assert done.await_count == (0 if during_startup else 1)
    finally:
        closed.set()
        master.shutdown()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("failure", ["frontend", "addon_halt", "native"])
async def test_shutdown_does_not_depend_on_done_hooks(monkeypatch, failure):
    server = Mock(wait_closed=AsyncMock())
    if failure == "native":
        server.wait_closed.side_effect = RuntimeError("native shutdown failed")
    monkeypatch.setattr(LocalRedirectorInstance, "_server", server)
    monkeypatch.setattr(LocalRedirectorInstance, "_instance", None)
    master = Master(None)
    ps = Proxyserver()
    monkeypatch.setattr(ps, "setup_servers", AsyncMock(return_value=True))

    class Halt:
        def done(self):
            raise exceptions.AddonHalt()

    if failure == "addon_halt":
        master.addons.add(Halt())
    master.addons.add(ps)

    async def running():
        ps.running()
        master.shutdown()

    monkeypatch.setattr(master, "running", running)
    if failure == "frontend":
        monkeypatch.setattr(
            master,
            "done",
            AsyncMock(side_effect=RuntimeError("frontend teardown failed")),
        )
    try:
        if failure == "addon_halt":
            await master.run()
        else:
            message = (
                "frontend teardown failed"
                if failure == "frontend"
                else "native shutdown failed"
            )
            with pytest.raises(RuntimeError, match=message):
                await master.run()
        server.close.assert_called_once()
        server.wait_closed.assert_awaited_once()
        if failure != "native":
            assert LocalRedirectorInstance._server is None
    finally:
        master._legacy_log_events.uninstall()
