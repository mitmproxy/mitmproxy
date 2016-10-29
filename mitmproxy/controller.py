import functools
import queue
from mitmproxy import exceptions


class Channel:
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
        m.reply._state = "committed"  # suppress error message in __del__
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

        # DummyReplys may be reused multiple times.
        # We only clear them up on the next handler so that we can access value and
        # state in the meantime.
        if isinstance(message.reply, DummyReply):
            message.reply.reset()

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
        if handling and message.reply.state == "handled":
            message.reply.take()
            if not message.reply.has_message:
                message.reply.ack()
            message.reply.commit()

            # DummyReplys may be reused multiple times.
            if isinstance(message.reply, DummyReply):
                message.reply.mark_reset()
        return ret
    # Mark this function as a handler wrapper
    wrapper.__dict__["__handler"] = True
    return wrapper


NO_REPLY = object()  # special object we can distinguish from a valid "None" reply.


class Reply:
    """
    Messages sent through a channel are decorated with a "reply" attribute.
    This object is used to respond to the message through the return
    channel.
    """
    def __init__(self, obj):
        self.obj = obj
        self.q = queue.Queue()  # type: queue.Queue

        self._state = "unhandled"  # "unhandled" -> "handled" -> "taken" -> "committed"
        self.value = NO_REPLY  # holds the reply value. May change before things are actually commited.

    @property
    def state(self):
        """
        The state the reply is currently in. A normal reply object goes sequentially through the following lifecycle:

            1. unhandled: Initial State.
            2. handled: The reply object has been handled by the topmost handler function.
            3. taken: The reply object has been taken to be commited.
            4. committed: The reply has been sent back to the requesting party.

        This attribute is read-only and can only be modified by calling one of state transition functions.
        """
        return self._state

    @property
    def has_message(self):
        return self.value != NO_REPLY

    def handle(self):
        """
        Reply are handled by controller.handlers, which may be nested. The first handler takes
        responsibility and handles the reply.
        """
        if self.state != "unhandled":
            raise exceptions.ControlException("Reply is {}, but expected it to be unhandled.".format(self.state))
        self._state = "handled"

    def take(self):
        """
        Scripts or other parties make "take" a reply out of a normal flow.
        For example, intercepted flows are taken out so that the connection thread does not proceed.
        """
        if self.state != "handled":
            raise exceptions.ControlException("Reply is {}, but expected it to be handled.".format(self.state))
        self._state = "taken"

    def commit(self):
        """
        Ultimately, messages are commited. This is done either automatically by the handler
        if the message is not taken or manually by the entity which called .take().
        """
        if self.state != "taken":
            raise exceptions.ControlException("Reply is {}, but expected it to be taken.".format(self.state))
        if not self.has_message:
            raise exceptions.ControlException("There is no reply message.")
        self._state = "committed"
        self.q.put(self.value)

    def ack(self, force=False):
        self.send(self.obj, force)

    def kill(self, force=False):
        self.send(exceptions.Kill, force)

    def send(self, msg, force=False):
        if self.state not in ("handled", "taken"):
            raise exceptions.ControlException(
                "Reply is {}, did not expect a call to .send().".format(self.state)
            )
        if self.has_message and not force:
            raise exceptions.ControlException("There is already a reply message.")
        self.value = msg

    def __del__(self):
        if self.state != "committed":
            # This will be ignored by the interpreter, but emit a warning
            raise exceptions.ControlException("Uncommitted reply: %s" % self.obj)


class DummyReply(Reply):
    """
    A reply object that is not connected to anything. In contrast to regular
    Reply objects, DummyReply objects are reset to "unhandled" at the end of an
    handler so that they can be used multiple times. Useful when we need an
    object to seem like it has a channel, and during testing.
    """
    def __init__(self):
        super().__init__(None)
        self._should_reset = False

    def mark_reset(self):
        if self.state != "committed":
            raise exceptions.ControlException("Uncommitted reply: %s" % self.obj)
        self._should_reset = True

    def reset(self):
        if self._should_reset:
            self._state = "unhandled"
            self.value = NO_REPLY

    def __del__(self):
        pass
