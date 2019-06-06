import time

from typing import List

from mitmproxy import flow
from mitmproxy.coretypes import serializable

from h2 import events


class HTTP2Frame(serializable.Serializable):

    def __init__(self, from_client, events, timestamp=None):
        self.from_client = from_client
        self.events: List[events.Event] = events
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client, self.content, self.timestamp = state

    def __repr__(self):
        # TODO Improve message
        return "{direction} {content}".format(
            direction="->" if self.from_client else "<-",
            content=repr(self.content)
        )


class HTTP2Flow(flow.Flow):

    """
    A Http2Flow is a simplified representation of a Http/2 connection
    """

    def __init__(self, client_conn, server_conn, live=None):
        super().__init__("http2", client_conn, server_conn, live)
        self.messages: List[Http2Frame] = []

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["messages"] = List[HTTP2Frame]

    def __repr__(self):
        return "<Http2Flow ({} messages)>".format(len(self.messages))
