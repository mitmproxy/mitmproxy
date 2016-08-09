from __future__ import absolute_import, print_function, division

import functools
import threading
import contextlib

from six.moves import queue

from mitmproxy import addons
from mitmproxy import options
from . import ctx as mitmproxy_ctx
from netlib import basethread
from . import exceptions


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

    "start",
    "configure",
    "done",
    "tick",
])


class Log(object):
    def __init__(self, master):
        self.master = master

    def __call__(self, text, level="info"):
        self.master.add_log(text, level)

    def debug(self, txt):
        self(txt, "debug")

    def info(self, txt):
        self(txt, "info")

    def warn(self, txt):
        self(txt, "warn")

    def error(self, txt):
        self(txt, "error")


class Master(object):
    """
        The master handles mitmproxy's main event loop.
    """
    def __init__(self, opts, *servers):
        self.options = opts or options.Options()
        self.addons = addons.Addons(self)
        self.event_queue = queue.Queue()
        self.should_exit = threading.Event()
        self.servers = []
        for i in servers:
            self.add_server(i)

    @contextlib.contextmanager
    def handlecontext(self):
        # Handlecontexts also have to nest - leave cleanup to the outermost
        if mitmproxy_ctx.master:
            yield
            return
        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = Log(self)
        try:
            yield
        finally:
            mitmproxy_ctx.master = None
            mitmproxy_ctx.log = None

    def add_log(self, e, level="info"):
        """
            level: debug, info, warn, error
        """

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
        with self.handlecontext():
            self.addons("tick")
        changed = False
        try:
            mtype, obj = self.event_queue.get(timeout=timeout)
            if mtype not in Events:
                raise exceptions.ControlException("Unknown event %s" % repr(mtype))
            handle_func = getattr(self, mtype)
            if not callable(handle_func):
                raise exceptions.ControlException("Handler %s not callable" % mtype)
            if not handle_func.__dict__.get("__handler"):
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
        self.addons.done()


class ServerThread(basethread.BaseThread):
    def __init__(self, server):
        self.server = server
        address = getattr(self.server, "address", None)
        super(ServerThread, self).__init__(
            "ServerThread ({})".format(repr(address))
        )

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
    def wrapper(master, message):
        if not hasattr(message, "reply"):
            raise exceptions.ControlException("Message %s has no reply attribute" % message)

        # The following ensures that inheritance with wrapped handlers in the
        # base class works. If we're the first handler, then responsibility for
        # acking is ours. If not, it's someone else's and we ignore it.
        handling = False
        # We're the first handler - ack responsibility is ours
        if message.reply.state == "unhandled":
            handling = True
            message.reply.handle()

        with master.handlecontext():
            ret = f(master, message)
            if handling:
                master.addons(f.__name__, message)

        # Reset the handled flag - it's common for us to feed the same object
        # through handlers repeatedly, so we don't want this to persist across
        # calls.
        if handling and not message.reply.taken:
            if message.reply.value == NO_REPLY:
                message.reply.ack()
            message.reply.commit()
        return ret
    # Mark this function as a handler wrapper
    wrapper.__dict__["__handler"] = True
    return wrapper


NO_REPLY = object()  # special object we can distinguish from a valid "None" reply.


class Reply(object):
    """
    Messages sent through a channel are decorated with a "reply" attribute.
    This object is used to respond to the message through the return
    channel.
    """
    def __init__(self, obj):
        self.obj = obj
        self.q = queue.Queue()

        self.state = "unhandled"  # "unhandled" -> "handled" -> "taken" -> "committed"
        self.value = NO_REPLY  # holds the reply value. May change before things are actually commited.

    def handle(self):
        """
        Reply are handled by controller.handlers, which may be nested. The first handler takes
        responsibility and handles the reply.
        """
        if self.state != "unhandled":
            raise exceptions.ControlException("Message is {}, but expected it to be unhandled.".format(self.state))
        self.state = "handled"

    def take(self):
        """
        Scripts or other parties make "take" a reply out of a normal flow.
        For example, intercepted flows are taken out so that the connection thread does not proceed.
        """
        if self.state != "handled":
            raise exceptions.ControlException("Message is {}, but expected it to be handled.".format(self.state))
        self.state = "taken"

    def commit(self):
        """
        Ultimately, messages are commited. This is done either automatically by the handler
        if the message is not taken or manually by the entity which called .take().
        """
        if self.state != "taken":
            raise exceptions.ControlException("Message is {}, but expected it to be taken.".format(self.state))
        self.state = "committed"
        self.q.put(self.value)

    def ack(self):
        self.send(self.obj)

    def kill(self):
        self.send(exceptions.Kill)

    def send(self, msg):
        if self.state not in ("handled", "taken"):
            raise exceptions.ControlException(
                "Reply is currently {}, did not expect a call to .send().".format(self.state)
            )
        if self.value is not NO_REPLY:
            raise exceptions.ControlException("There is already a reply for this message.")
        self.value = msg

    def __del__(self):
        if self.state != "comitted":
            # This will be ignored by the interpreter, but emit a warning
            raise exceptions.ControlException("Uncomitted message: %s" % self.obj)


class DummyReply(Reply):
    """
    A reply object that is not connected to anything. In contrast to regular Reply objects,
    DummyReply objects are reset to "unhandled" after a commit so that they can be used
    multiple times. Useful when we need an object to seem like it has a channel,
    and during testing.
    """
    def __init__(self):
        super(DummyReply, self).__init__(None)

    def commit(self):
        super(DummyReply, self).commit()
        self.state = "unhandled"
        self.value = NO_REPLY
