import asyncio
import pytest
from mitmproxy.utils.signals import AsyncSignal, SyncSignal


async def test_async_connect_to_sync():
    is_connected = False
    was_called = False

    def valid(sender):
        nonlocal was_called
        was_called = True

    async def invalid(sender):
        assert False

    def check_connected(signal, receiver, sender, weak):
        nonlocal is_connected
        assert receiver is valid
        is_connected = True

    signal = SyncSignal()
    signal.receiver_connected.connect(check_connected)
    with pytest.raises(TypeError, match="cannot be an asynchronous function"):
        signal.connect(invalid)
    signal.connect(valid)
    assert is_connected

    signal.send(signal)
    assert was_called


async def test_async_returned_in_sync():
    is_connected = False

    def delayed_invalid(sender):
        async def invalid():
            await asyncio.sleep(1)
            return True

        return invalid()

    def check_connected(signal, receiver, sender, weak):
        nonlocal is_connected
        assert receiver is delayed_invalid
        is_connected = True

    signal = SyncSignal()
    signal.receiver_connected.connect(check_connected)
    signal.connect(delayed_invalid)
    assert is_connected

    with pytest.raises(RuntimeError, match="returned awaitable"):
        signal.send(signal)


async def test_async():
    is_connected_sync = False
    is_connected_async = False
    async_ret = object()
    sync_ret = object()

    async def delayed(sender):
        nonlocal async_ret
        await asyncio.sleep(1)
        return async_ret

    async def immediate(sender):
        nonlocal sync_ret
        return sync_ret

    def check_connected(signal, receiver, sender, weak):
        nonlocal is_connected_sync, is_connected_async
        if receiver is delayed:
            is_connected_async = True
        elif receiver is immediate:
            is_connected_sync = True
        else:
            assert False

    signal = AsyncSignal()
    signal.receiver_connected.connect(check_connected)
    signal.connect(delayed)
    signal.connect(immediate)
    assert is_connected_async and is_connected_sync

    res = await signal.send(signal)
    assert len(res) == 2
    for receiver, ret in res:
        if receiver is delayed:
            assert ret is async_ret
        elif receiver is immediate:
            assert ret is sync_ret
        else:
            assert False
