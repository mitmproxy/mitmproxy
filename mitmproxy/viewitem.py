import typing  # noqa
import uuid

from mitmproxy import controller, exceptions  # noqa
from mitmproxy import stateobject
from mitmproxy import flow


class ViewItem(stateobject.StateObject):

    """
    A ViewItem is a collection of objects representing a single transaction.
    This class is usually subclassed for each protocol, e.g. HTTP2Message.
    """

    def __init__(self, flow: flow.Flow) -> None:
        self.id = str(uuid.uuid4())

        self.marked: bool = False
        self.flow: flow.Flow = flow
