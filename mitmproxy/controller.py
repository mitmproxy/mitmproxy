from __future__ import absolute_import, print_function, division

import functools
import threading

from six.moves import queue

from mitmproxy import exceptions

Events = frozenset([
    "clientconnect",
    "clientdisconnect",
    "serverconnect",
    "serverdisconnect",

    "tcp_open",
    "tcp_message",
    "tcp_error",
    "tcp_close",

    "request",
    "response",
    "responseheaders",

    "next_layer",

    "error",
    "log",

    "script_change",
])


class Master(object):
    """
        The master handles mitmproxy's main event loop.
    """
    def __init__(self, *servers):
        self.event_queue = queue.Queue()
        self.should_exit = threading.Event()
        self.servers = []
        for i in servers:
            self.add_server(i)

    def add_server(self, server):
        # We give a Channel to the server which can be used to communicate with the master
        channel = Channel(self.event_queue, self.should_exit)
        server.set_channel(channel)
        self.servers.append(server)

    def start(self):
        self.should_exit.clear()
        for server in self.servers:
            ServerThread(server).start()

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
                if mtype not in Events:
                    raise exceptions.ControlException("Unknown event %s" % repr(mtype))
                handle_func = getattr(self, mtype)
                if not hasattr(handle_func, "func_dict"):
                    raise exceptions.ControlException("Handler %s not a function" % mtype)
                if not handle_func.func_dict.get("__handler"):
                    raise exceptions.ControlException(
                        "Handler function %s is not decorated with controller.handler" % (
                            handle_func
                        )
                    )
                handle_func(obj)
                self.event_queue.task_done()
                changed = True
        except queue.Empty:
            pass
        return changed

    def shutdown(self):
        for server in self.servers:
            server.shutdown()
        self.should_exit.set()


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
            exceptions.Kill: All connections should be closed immediately.
        """
        m.reply = Reply(m)
        self.q.put((mtype, m))
        while not self.should_exit.is_set():
            try:
                # The timeout is here so we can handle a should_exit event.
                g = m.reply.q.get(timeout=0.5)
            except queue.Empty:  # pragma: no cover
                continue
            if g == exceptions.Kill:
                raise exceptions.Kill()
            return g
        raise exceptions.Kill()

    def tell(self, mtype, m):
        """
        Decorate a message with a dummy reply attribute, send it to the
        master, then return immediately.
        """
        m.reply = DummyReply()
        self.q.put((mtype, m))


def handler(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # We can either be called as a method, or as a wrapped solo function
        if len(args) == 1:
            message = args[0]
        elif len(args) == 2:
            message = args[1]
        else:
            raise exceptions.ControlException("Handler takes one argument: a message")

        if not hasattr(message, "reply"):
            raise exceptions.ControlException("Message %s has no reply attribute" % message)

        # The following ensures that inheritance with wrapped handlers in the
        # base class works. If we're the first handler, then responsibility for
        # acking is ours. If not, it's someone else's and we ignore it.
        handling = False
        # We're the first handler - ack responsibility is ours
        if not message.reply.handled:
            handling = True
            message.reply.handled = True

        ret = f(*args, **kwargs)

        if handling and not message.reply.acked and not message.reply.taken:
            message.reply.ack()
        return ret
    # Mark this function as a handler wrapper
    wrapper.func_dict["__handler"] = True
    return wrapper


class Reply(object):
    """
    Messages sent through a channel are decorated with a "reply" attribute.
    This object is used to respond to the message through the return
    channel.
    """
    def __init__(self, obj):
        self.obj = obj
        self.q = queue.Queue()
        # Has this message been acked?
        self.acked = False
        # Has the user taken responsibility for ack-ing?
        self.taken = False
        # Has a handler taken responsibility for ack-ing?
        self.handled = False

    def ack(self):
        self.send(self.obj)

    def kill(self):
        self.send(exceptions.Kill)

    def take(self):
        self.taken = True

    def send(self, msg):
        if self.acked:
            raise exceptions.ControlException("Message already acked.")
        self.acked = True
        self.q.put(msg)

    def __del__(self):
        if not self.acked:
            # This will be ignored by the interpreter, but emit a warning
            raise exceptions.ControlException("Un-acked message")


class DummyReply(object):
    """
    A reply object that does nothing. Useful when we need an object to seem
    like it has a channel, and during testing.
    """
    def __init__(self):
        self.acked = False
        self.taken = False
        self.handled = False

    def kill(self):
        self.send(None)

    def ack(self):
        self.send(None)

    def take(self):
        self.taken = True

    def send(self, msg):
        self.acked = True
