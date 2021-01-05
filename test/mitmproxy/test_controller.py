import asyncio

import pytest

import mitmproxy.ctx
from mitmproxy import controller
from mitmproxy.exceptions import ControlException
from mitmproxy.test import taddons


@pytest.mark.asyncio
async def test_master():
    class tAddon:
        def add_log(self, _):
            mitmproxy.ctx.master.should_exit.set()

    with taddons.context(tAddon()) as tctx:
        assert not tctx.master.should_exit.is_set()

        async def test():
            mitmproxy.ctx.log("test")

        asyncio.ensure_future(test())
        await tctx.master.await_log("test")
        assert tctx.master.should_exit.is_set()


class TestReply:
    @pytest.mark.asyncio
    async def test_simple(self):
        reply = controller.Reply(42)
        assert reply.state == "start"

        reply.take()
        assert reply.state == "taken"

        assert not reply.done.is_set()
        reply.commit()
        assert reply.state == "committed"
        assert await asyncio.wait_for(reply.done.wait(), 1)

    def test_double_commit(self):
        reply = controller.Reply(47)
        reply.take()
        reply.commit()
        with pytest.raises(ControlException):
            reply.commit()

    def test_del(self):
        reply = controller.Reply(47)
        with pytest.raises(ControlException):
            reply.__del__()
        reply.take()
        reply.commit()


class TestDummyReply:
    def test_simple(self):
        reply = controller.DummyReply()
        for _ in range(2):
            reply.take()
            reply.commit()
            reply.mark_reset()
            reply.reset()
        assert reply.state == "start"

    def test_reset(self):
        reply = controller.DummyReply()
        reply.take()
        with pytest.raises(ControlException):
            reply.mark_reset()
        reply.commit()
        reply.mark_reset()
        assert reply.state == "committed"
        reply.reset()
        assert reply.state == "start"

    def test_del(self):
        reply = controller.DummyReply()
        reply.__del__()
