from __future__ import absolute_import
from six.moves import queue
import threading


class DummyReply:

    """
        A reply object that does nothing. Useful when we need an object to seem
        like it has a channel, and during testing.
    """

    def __init__(self):
        self.acked = False

    def __call__(self, msg=False):
        self.acked = True


class Reply:

    """
        Messages sent through a channel are decorated with a "reply" attribute.
        This object is used to respond to the message through the return
        channel.
    """

    def __init__(self, obj):
        self.obj = obj
        self.q = queue.Queue()
        self.acked = False

    def __call__(self, msg=None):
        if not self.acked:
            self.acked = True
            if msg is None:
                self.q.put(self.obj)
            else:
                self.q.put(msg)


class Channel:

    def __init__(self, q, should_exit):
        self.q = q
        self.should_exit = should_exit

    def ask(self, mtype, m):
        """
            Decorate a message with a reply attribute, and send it to the
            master.  then wait for a response.
        """
        m.reply = Reply(m)
        self.q.put((mtype, m))
        while not self.should_exit.is_set():
            try:
                # The timeout is here so we can handle a should_exit event.
                g = m.reply.q.get(timeout=0.5)
            except queue.Empty:  # pragma: no cover
                continue
            return g

    def tell(self, mtype, m):
        """
            Decorate a message with a dummy reply attribute, send it to the
            master, then return immediately.
        """
        m.reply = DummyReply()
        self.q.put((mtype, m))


class Slave(threading.Thread):

    """
        Slaves get a channel end-point through which they can send messages to
        the master.
    """

    def __init__(self, channel, server):
        self.channel, self.server = channel, server
        self.server.set_channel(channel)
        threading.Thread.__init__(self)
        self.name = "SlaveThread (%s:%s)" % (
            self.server.address.host, self.server.address.port)

    def run(self):
        self.server.serve_forever()


class Master(object):

    """
        Masters get and respond to messages from slaves.
    """

    def __init__(self, server):
        """
            server may be None if no server is needed.
        """
        self.server = server
        self.masterq = queue.Queue()
        self.should_exit = threading.Event()

    def tick(self, q, timeout):
        changed = False
        try:
            # This endless loop runs until the 'Queue.Empty'
            # exception is thrown. If more than one request is in
            # the queue, this speeds up every request by 0.1 seconds,
            # because get_input(..) function is not blocking.
            while True:
                msg = q.get(timeout=timeout)
                self.handle(*msg)
                q.task_done()
                changed = True
        except queue.Empty:
            pass
        return changed

    def run(self):
        self.should_exit.clear()
        self.server.start_slave(Slave, Channel(self.masterq, self.should_exit))
        while not self.should_exit.is_set():

            # Don't choose a very small timeout in Python 2:
            # https://github.com/mitmproxy/mitmproxy/issues/443
            # TODO: Lower the timeout value if we move to Python 3.
            self.tick(self.masterq, 0.1)
        self.shutdown()

    def handle(self, mtype, obj):
        c = "handle_" + mtype
        m = getattr(self, c, None)
        if m:
            m(obj)
        else:
            obj.reply()

    def shutdown(self):
        if not self.should_exit.is_set():
            self.should_exit.set()
            if self.server:
                self.server.shutdown()
