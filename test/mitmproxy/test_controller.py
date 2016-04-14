from threading import Thread, Event

from mock import Mock

from mitmproxy.controller import Reply, DummyReply, Channel, ServerThread, ServerMaster, Master
from six.moves import queue

from mitmproxy.exceptions import Kill
from mitmproxy.proxy import DummyServer
from netlib.tutils import raises


class TestMaster(object):
    def test_simple(self):

        class DummyMaster(Master):
            def handle_panic(self, _):
                m.should_exit.set()

            def tick(self, timeout):
                # Speed up test
                super(DummyMaster, self).tick(0)

        m = DummyMaster()
        assert not m.should_exit.is_set()
        m.event_queue.put(("panic", 42))
        m.run()
        assert m.should_exit.is_set()


class TestServerMaster(object):
    def test_simple(self):
        m = ServerMaster()
        s = DummyServer(None)
        m.add_server(s)
        m.start()
        m.shutdown()
        m.start()
        m.shutdown()


class TestServerThread(object):
    def test_simple(self):
        m = Mock()
        t = ServerThread(m)
        t.run()
        assert m.serve_forever.called


class TestChannel(object):
    def test_tell(self):
        q = queue.Queue()
        channel = Channel(q, Event())
        m = Mock()
        channel.tell("test", m)
        assert q.get() == ("test", m)
        assert m.reply

    def test_ask_simple(self):
        q = queue.Queue()

        def reply():
            m, obj = q.get()
            assert m == "test"
            obj.reply(42)

        Thread(target=reply).start()

        channel = Channel(q, Event())
        assert channel.ask("test", Mock()) == 42

    def test_ask_shutdown(self):
        q = queue.Queue()
        done = Event()
        done.set()
        channel = Channel(q, done)
        with raises(Kill):
            channel.ask("test", Mock())


class TestDummyReply(object):
    def test_simple(self):
        reply = DummyReply()
        assert not reply.acked
        reply()
        assert reply.acked


class TestReply(object):
    def test_simple(self):
        reply = Reply(42)
        assert not reply.acked
        reply("foo")
        assert reply.acked
        assert reply.q.get() == "foo"

    def test_default(self):
        reply = Reply(42)
        reply()
        assert reply.q.get() == 42

    def test_reply_none(self):
        reply = Reply(42)
        reply(None)
        assert reply.q.get() is None
