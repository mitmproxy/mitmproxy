import queue
import asyncio
from mitmproxy import exceptions


class Channel:
    """
        The only way for the proxy server to communicate with the master
        is to use the channel it has been given.
    """
    def __init__(self, master, loop, should_exit):
        self.master = master
        self.loop = loop
        self.should_exit = should_exit

    def ask(self, mtype, m):
        """
        Decorate a message with a reply attribute, and send it to the master.
        Then wait for a response.

        Raises:
            exceptions.Kill: All connections should be closed immediately.
        """
        if not self.should_exit.is_set():
            m.reply = Reply(m)
            asyncio.run_coroutine_threadsafe(
                self.master.addons.handle_lifecycle(mtype, m),
                self.loop,
            )
            g = m.reply.q.get()
            if g == exceptions.Kill:
                raise exceptions.Kill()
            return g

    def tell(self, mtype, m):
        """
        Decorate a message with a dummy reply attribute, send it to the master,
        then return immediately.
        """
        if not self.should_exit.is_set():
            m.reply = DummyReply()
            asyncio.run_coroutine_threadsafe(
                self.master.addons.handle_lifecycle(mtype, m),
                self.loop,
            )


NO_REPLY = object()  # special object we can distinguish from a valid "None" reply.


class Reply:
    """
    Messages sent through a channel are decorated with a "reply" attribute. This
    object is used to respond to the message through the return channel.
    """
    def __init__(self, obj):
        self.obj = obj
        # Spawn an event loop in the current thread
        self.q = queue.Queue()

        self._state = "start"  # "start" -> "taken" -> "committed"

        # Holds the reply value. May change before things are actually committed.
        self.value = NO_REPLY

    @property
    def state(self):
        """
        The state the reply is currently in. A normal reply object goes
        sequentially through the following lifecycle:

            1. start: Initial State.
            2. taken: The reply object has been taken to be committed.
            3. committed: The reply has been sent back to the requesting party.

        This attribute is read-only and can only be modified by calling one of
        state transition functions.
        """
        return self._state

    @property
    def has_message(self):
        return self.value != NO_REPLY

    def take(self):
        """
        Scripts or other parties make "take" a reply out of a normal flow.
        For example, intercepted flows are taken out so that the connection thread does not proceed.
        """
        if self.state != "start":
            raise exceptions.ControlException(
                "Reply is {}, but expected it to be start.".format(self.state)
            )
        self._state = "taken"

    def commit(self):
        """
        Ultimately, messages are committed. This is done either automatically by
        the handler if the message is not taken or manually by the entity which
        called .take().
        """
        if self.state != "taken":
            raise exceptions.ControlException(
                "Reply is {}, but expected it to be taken.".format(self.state)
            )
        if not self.has_message:
            raise exceptions.ControlException("There is no reply message.")
        self._state = "committed"
        self.q.put(self.value)

    def ack(self, force=False):
        self.send(self.obj, force)

    def kill(self, force=False):
        self.send(exceptions.Kill, force)
        if self._state == "taken":
            self.commit()

    def send(self, msg, force=False):
        if self.state not in {"start", "taken"}:
            raise exceptions.ControlException(
                "Reply is {}, but expected it to be start or taken.".format(self.state)
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
    Reply objects, DummyReply objects are reset to "start" at the end of an
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
            self._state = "start"
            self.value = NO_REPLY

    def __del__(self):
        pass
