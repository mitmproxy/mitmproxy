import time
import typing  # noqa
import uuid

from mitmproxy import connections
from mitmproxy import controller, exceptions  # noqa
from mitmproxy import stateobject
from mitmproxy import version


class ViewItem(stateobject.StateObject):

    """
    A ViewItem is a collection of objects representing a single transaction.
    This class is usually subclassed for each protocol, e.g. HTTP2Message.
    """

    def __init__(self) -> None:
        self.id = str(uuid.uuid4())

        self.reply: typing.Optional[controller.Reply] = None
        self.marked: bool = False
        self.intercepted: bool = False

    @property
    def killable(self):
        return (
            hasattr(self, "reply") and
            self.reply and
            self.reply.state in {"start", "taken"} and
            self.reply.value != exceptions.Kill
        )

    def kill(self):
        """
            Kill this item
        """
        raise NotImplementedError()


