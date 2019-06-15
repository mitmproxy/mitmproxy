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

    def intercept(self):
        """
            Intercept this Flow. Processing will stop until resume is
            called.
        """
        if self.intercepted:
            return
        self.intercepted = True
        self.reply.take()

    def resume(self):
        """
            Continue with the flow - called after an intercept().
        """
        if not self.intercepted:
            return
        self.intercepted = False
        # If a flow is intercepted and then duplicated, the duplicated one is not taken.
        if self.reply.state == "taken":
            self.reply.ack()
            self.reply.commit()
