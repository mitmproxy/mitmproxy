from __future__ import absolute_import
from six.moves import queue
import threading

from .exceptions import Kill


class Master(object):

    """
    The master handles mitmproxy's main event loop.
    """

    def __init__(self):
        self.event_queue = queue.Queue()
        self.should_exit = threading.Event()

    def start(self):
        self.should_exit.clear()

    def run(self):
        self.start()
        try:
            while not self.should_exit.is_set():
                # Don't choose a very small timeout in Python 2:
                # https://github.com/mitmproxy/mitmproxy/issues/443
                # TODO: Lower the timeout value if we move to Python 3.
                self.tick(0.1)
        finally:
            self.shutdown()

    def tick(self, timeout):
        changed = False
        try:
            # This endless loop runs until the 'Queue.Empty'
            # exception is thrown.
            while True:
                mtype, obj = self.event_queue.get(timeout=timeout)
                handle_func = getattr(self, "handle_" + mtype)
                handle_func(obj)
                self.event_queue.task_done()
                changed = True
        except queue.Empty:
            pass
        return changed

    def shutdown(self):
        self.should_exit.set()


class ServerMaster(Master):

    """
    The ServerMaster adds server thread support to the master.
    """

    def __init__(self):
        super(ServerMaster, self).__init__()
        self.servers = []

    def add_server(self, server):
        # We give a Channel to the server which can be used to communicate with the master
        channel = Channel(self.event_queue, self.should_exit)
        server.set_channel(channel)
        self.servers.append(server)

    def start(self):
        super(ServerMaster, self).start()
        for server in self.servers:
            ServerThread(server).start()

    def shutdown(self):
        for server in self.servers:
            server.shutdown()
        super(ServerMaster, self).shutdown()


class ServerThread(threading.Thread):

    def __init__(self, server):
        self.server = server
        super(ServerThread, self).__init__()
        address = getattr(self.server, "address", None)
        self.name = "ServerThread ({})".format(repr(address))

    def run(self):
        self.server.serve_forever()


class Channel(object):

    """
    The only way for the proxy server to communicate with the master
    is to use the channel it has been given.
    """

    def __init__(self, q, should_exit):
        self.q = q
        self.should_exit = should_exit

    def ask(self, mtype, m):
        """
        Decorate a message with a reply attribute, and send it to the
        master. Then wait for a response.

        Raises:
            Kill: All connections should be closed immediately.
        """
        m.reply = Reply(m)
        self.q.put((mtype, m))
        while not self.should_exit.is_set():
            try:
                # The timeout is here so we can handle a should_exit event.
                g = m.reply.q.get(timeout=0.5)
            except queue.Empty:  # pragma: no cover
                continue
            if g == Kill:
                raise Kill()
            return g

        raise Kill()

    def tell(self, mtype, m):
        """
        Decorate a message with a dummy reply attribute, send it to the
        master, then return immediately.
        """
        m.reply = DummyReply()
        self.q.put((mtype, m))


class DummyReply(object):

    """
    A reply object that does nothing. Useful when we need an object to seem
    like it has a channel, and during testing.
    """

    def __init__(self):
        self.acked = False

    def __call__(self, msg=False):
        self.acked = True


# Special value to distinguish the case where no reply was sent
NO_REPLY = object()


class Reply(object):

    """
    Messages sent through a channel are decorated with a "reply" attribute.
    This object is used to respond to the message through the return
    channel.
    """

    def __init__(self, obj):
        self.obj = obj
        self.q = queue.Queue()
        self.acked = False

    def __call__(self, msg=NO_REPLY):
        if not self.acked:
            self.acked = True
            if msg is NO_REPLY:
                self.q.put(self.obj)
            else:
                self.q.put(msg)
