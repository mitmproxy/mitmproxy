import time

from typing import List

from mitmproxy import flow
from mitmproxy.coretypes import serializable


class TCPMessage(serializable.Serializable):

    def __init__(self, from_client, content, timestamp=None):
        self.from_client = from_client
        self.content = content
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client, self.content, self.timestamp = state

    def __repr__(self):
        return "{direction} {content}".format(
            direction="->" if self.from_client else "<-",
            content=repr(self.content)
        )


class TCPFlow(flow.Flow):

    """
    A TCPFlow is a simplified representation of a TCP session.
    """

    def __init__(self, client_conn, server_conn, live=None):
        super().__init__("tcp", client_conn, server_conn, live)
        self.messages: List[TCPMessage] = []

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["messages"] = List[TCPMessage]

    def __repr__(self):
        return "<TCPFlow ({} messages)>".format(len(self.messages))
