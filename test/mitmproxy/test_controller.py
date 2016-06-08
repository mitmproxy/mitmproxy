from threading import Thread, Event

from mock import Mock

from mitmproxy import controller
from six.moves import queue

from mitmproxy.exceptions import Kill
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

        m = DummyMaster()
        assert not m.should_exit.is_set()
        msg = TMsg()
        msg.reply = controller.DummyReply()
        m.event_queue.put(("log", msg))
        m.run()
        assert m.should_exit.is_set()

    def test_server_simple(self):
        m = controller.Master()
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
        m = Mock()
        channel.tell("test", m)
        assert q.get() == ("test", m)
        assert m.reply

    def test_ask_simple(self):
        q = queue.Queue()

        def reply():
            m, obj = q.get()
            assert m == "test"
            obj.reply.send(42)

        Thread(target=reply).start()

        channel = controller.Channel(q, Event())
        assert channel.ask("test", Mock()) == 42

    def test_ask_shutdown(self):
        q = queue.Queue()
        done = Event()
        done.set()
        channel = controller.Channel(q, done)
        with raises(Kill):
            channel.ask("test", Mock())


class TestDummyReply(object):
    def test_simple(self):
        reply = controller.DummyReply()
        assert not reply.acked
        reply.ack()
        assert reply.acked


class TestReply(object):
    def test_simple(self):
        reply = controller.Reply(42)
        assert not reply.acked
        reply.send("foo")
        assert reply.acked
        assert reply.q.get() == "foo"

    def test_default(self):
        reply = controller.Reply(42)
        reply.ack()
        assert reply.q.get() == 42

    def test_reply_none(self):
        reply = controller.Reply(42)
        reply.send(None)
        assert reply.q.get() is None
