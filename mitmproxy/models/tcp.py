import time
from typing import List

from netlib.utils import Serializable
from .flow import Flow


class TCPMessage(Serializable):

    def __init__(self, from_client, content, timestamp=None):
        self.content = content
        self.from_client = from_client
        if timestamp is None:
            timestamp = time.time()
        self.timestamp = timestamp

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client = state.pop("from_client")
        self.content = state.pop("content")
        self.timestamp = state.pop("timestamp")

    def __repr__(self):
        return "{direction} {content}".format(
            direction="->" if self.from_client else "<-",
            content=repr(self.content)
        )


class TCPFlow(Flow):

    """
    A TCPFlow is a simplified representation of a TCP session.
    """

    def __init__(self, client_conn, server_conn, live=None):
        super(TCPFlow, self).__init__("tcp", client_conn, server_conn, live)
        self.messages = []  # type: List[TCPMessage]

    _stateobject_attributes = Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        messages=List[TCPMessage]
    )

    def __repr__(self):
        return "<TCPFlow ({} messages)>".format(len(self.messages))
