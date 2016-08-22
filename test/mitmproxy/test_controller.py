from test.mitmproxy import tutils
from threading import Thread, Event

from mock import Mock

from mitmproxy import controller
from six.moves import queue

from mitmproxy.exceptions import Kill, ControlException
from mitmproxy.proxy import DummyServer
from netlib.tutils import raises


class TMsg:
    pass


class TestMaster(object):
    def test_simple(self):
        class DummyMaster(controller.Master):
            @controller.handler
            def log(self, _):
                m.should_exit.set()

            def tick(self, timeout):
                # Speed up test
                super(DummyMaster, self).tick(0)

        m = DummyMaster(None)
        assert not m.should_exit.is_set()
        msg = TMsg()
        msg.reply = controller.DummyReply()
        m.event_queue.put(("log", msg))
        m.run()
        assert m.should_exit.is_set()

    def test_server_simple(self):
        m = controller.Master(None)
        s = DummyServer(None)
        m.add_server(s)
        m.start()
        m.shutdown()
        m.start()
        m.shutdown()


class TestServerThread(object):
    def test_simple(self):
        m = Mock()
        t = controller.ServerThread(m)
        t.run()
        assert m.serve_forever.called


class TestChannel(object):
    def test_tell(self):
        q = queue.Queue()
        channel = controller.Channel(q, Event())
        m = Mock(name="test_tell")
        channel.tell("test", m)
        assert q.get() == ("test", m)
        assert m.reply

    def test_ask_simple(self):
        q = queue.Queue()

        def reply():
            m, obj = q.get()
            assert m == "test"
            obj.reply.handle()
            obj.reply.send(42)
            obj.reply.take()
            obj.reply.commit()

        Thread(target=reply).start()

        channel = controller.Channel(q, Event())
        assert channel.ask("test", Mock(name="test_ask_simple")) == 42

    def test_ask_shutdown(self):
        q = queue.Queue()
        done = Event()
        done.set()
        channel = controller.Channel(q, done)
        with raises(Kill):
            channel.ask("test", Mock(name="test_ask_shutdown"))


class TestReply(object):
    def test_simple(self):
        reply = controller.Reply(42)
        assert reply.state == "unhandled"

        reply.handle()
        assert reply.state == "handled"

        reply.send("foo")
        assert reply.value == "foo"

        reply.take()
        assert reply.state == "taken"

        with tutils.raises(queue.Empty):
            reply.q.get_nowait()
        reply.commit()
        assert reply.state == "committed"
        assert reply.q.get() == "foo"

    def test_kill(self):
        reply = controller.Reply(43)
        reply.handle()
        reply.kill()
        reply.take()
        reply.commit()
        assert reply.q.get() == Kill

    def test_ack(self):
        reply = controller.Reply(44)
        reply.handle()
        reply.ack()
        reply.take()
        reply.commit()
        assert reply.q.get() == 44

    def test_reply_none(self):
        reply = controller.Reply(45)
        reply.handle()
        reply.send(None)
        reply.take()
        reply.commit()
        assert reply.q.get() is None

    def test_commit_no_reply(self):
        reply = controller.Reply(46)
        reply.handle()
        reply.take()
        with tutils.raises(ControlException):
            reply.commit()
        reply.ack()
        reply.commit()

    def test_double_send(self):
        reply = controller.Reply(47)
        reply.handle()
        reply.send(1)
        with tutils.raises(ControlException):
            reply.send(2)
        reply.take()
        reply.commit()

    def test_state_transitions(self):
        states = {"unhandled", "handled", "taken", "committed"}
        accept = {
            "handle": {"unhandled"},
            "take": {"handled"},
            "commit": {"taken"},
            "ack": {"handled", "taken"},
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
                    with tutils.raises(ControlException):
                        getattr(r, fn)()
                r._state = "committed"  # hide warnings on deletion

    def test_del(self):
        reply = controller.Reply(47)
        with tutils.raises(ControlException):
            reply.__del__()
        reply.handle()
        reply.ack()
        reply.take()
        reply.commit()


class TestDummyReply(object):
    def test_simple(self):
        reply = controller.DummyReply()
        for _ in range(2):
            reply.handle()
            reply.ack()
            reply.take()
            reply.commit()
            reply.mark_reset()
            reply.reset()
        assert reply.state == "unhandled"

    def test_reset(self):
        reply = controller.DummyReply()
        reply.handle()
        reply.ack()
        reply.take()
        reply.commit()
        reply.mark_reset()
        assert reply.state == "committed"
        reply.reset()
        assert reply.state == "unhandled"

    def test_del(self):
        reply = controller.DummyReply()
        reply.__del__()
