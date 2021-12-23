import asyncio
import warnings
from typing import Any

from mitmproxy import exceptions, flow


class Reply:
    """
    Messages sent through a channel are decorated with a "reply" attribute. This
    object is used to respond to the message through the return channel.
    """

    def __init__(self, obj):
        self.obj: Any = obj
        self.done: asyncio.Event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._state: str = "start"  # "start" -> "taken" -> "committed"

    @property
    def state(self):
        """
        This is a docstring.

        :param arg1: This is the first argument.
        :type arg1: int

            This function does nothing in particular.

            Args:
                arg1
        (int): The first argument.

            Returns:
                bool or NoneType : Always returns True unless error occurs, then False or None if no value can be
        returned. 

           Examples of use :  >>> print(do_nothing()) # prints 'True' as expected  >>> do_nothing() # prints 'None' as there was an error and no
        return value could be determined
        """
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

    def take(self):
        """
        Scripts or other parties make "take" a reply out of a normal flow.
        For example, intercepted flows are taken out so that the connection thread does not proceed.
        """
        if self.state != "start":
            raise exceptions.ControlException(f"Reply is {self.state}, but expected it to be start.")
        self._state = "taken"

    def commit(self):
        """
        Ultimately, messages are committed. This is done either automatically by
        the handler if the message is not taken or manually by the entity which
        called .take().
        """
        if self.state != "taken":
            raise exceptions.ControlException(f"Reply is {self.state}, but expected it to be taken.")
        self._state = "committed"
        try:
            self._loop.call_soon_threadsafe(lambda: self.done.set())
        except RuntimeError:  # pragma: no cover
            pass  # event loop may already be closed.

    def kill(self, force=False):  # pragma: no cover
        warnings.warn("reply.kill() is deprecated, use flow.kill() or set the error attribute instead.",
                      DeprecationWarning, stacklevel=2)
        self.obj.error = flow.Error(flow.Error.KILLED_MESSAGE)

    def __del__(self):
        if self.state != "committed":
            # This will be ignored by the interpreter, but emit a warning
            raise exceptions.ControlException(f"Uncommitted reply: {self.obj}")

    def __deepcopy__(self, memo):
        # some parts of the console ui may use deepcopy, see https://github.com/mitmproxy/mitmproxy/issues/4916
        return memo.setdefault(id(self), DummyReply())


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
            raise exceptions.ControlException(f"Uncommitted reply: {self.obj}")
        self._should_reset = True

    def reset(self):
        if self._should_reset:
            self._state = "start"

    def __del__(self):
        pass
