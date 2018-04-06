import asyncio
import queue
import pytest

from mitmproxy.exceptions import Kill, ControlException
from mitmproxy import controller
from mitmproxy.test import taddons
import mitmproxy.ctx


@pytest.mark.asyncio
async def test_master():

    class tAddon:
        def log(self, _):
            ctx.master.should_exit.set()

    with taddons.context(tAddon()) as ctx:
        assert not ctx.master.should_exit.is_set()

        async def test():
            mitmproxy.ctx.log("test")

        asyncio.ensure_future(test())
        assert await ctx.master.await_log("test")
        assert ctx.master.should_exit.is_set()


class TestReply:
    def test_simple(self):
        reply = controller.Reply(42)
        assert reply.state == "start"

        reply.send("foo")
        assert reply.value == "foo"

        reply.take()
        assert reply.state == "taken"

        with pytest.raises(queue.Empty):
            reply.q.get_nowait()
        reply.commit()
        assert reply.state == "committed"
        assert reply.q.get() == "foo"

    def test_kill(self):
        reply = controller.Reply(43)
        reply.kill()
        reply.take()
        reply.commit()
        assert reply.q.get() == Kill

    def test_ack(self):
        reply = controller.Reply(44)
        reply.ack()
        reply.take()
        reply.commit()
        assert reply.q.get() == 44

    def test_reply_none(self):
        reply = controller.Reply(45)
        reply.send(None)
        reply.take()
        reply.commit()
        assert reply.q.get() is None

    def test_commit_no_reply(self):
        reply = controller.Reply(46)
        reply.take()
        with pytest.raises(ControlException):
            reply.commit()
        reply.ack()
        reply.commit()

    def test_double_send(self):
        reply = controller.Reply(47)
        reply.send(1)
        with pytest.raises(ControlException):
            reply.send(2)
        reply.take()
        reply.commit()

    def test_state_transitions(self):
        states = {"start", "taken", "committed"}
        accept = {
            "take": {"start"},
            "commit": {"taken"},
            "ack": {"start", "taken"},
        }
        for fn, ok in accept.items():
            for state in states:
                r = controller.Reply(48)
                r._state = state
                if fn == "commit":
                    r.value = 49
                if state in ok:
                    getattr(r, fn)()
                else:
                    with pytest.raises(ControlException):
                        getattr(r, fn)()
                r._state = "committed"  # hide warnings on deletion

    def test_del(self):
        reply = controller.Reply(47)
        with pytest.raises(ControlException):
            reply.__del__()
        reply.ack()
        reply.take()
        reply.commit()


class TestDummyReply:
    def test_simple(self):
        reply = controller.DummyReply()
        for _ in range(2):
            reply.ack()
            reply.take()
            reply.commit()
            reply.mark_reset()
            reply.reset()
        assert reply.state == "start"

    def test_reset(self):
        reply = controller.DummyReply()
        reply.ack()
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
