from mitmproxy import flow
from mitmproxy.coretypes import serializable
import time
from typing import List

from h2 import events


class HTTP2Frame(serializable.Serializable):

    def __init__(self, from_client, events, timestamp=None):
        self.from_client: bool = from_client
        self.events: List[events.Event] = events
        self.frame_type: str = self._detect_frame_type(events[0])
        self.stream_ID: int = events[0].stream_id if hasattr(events[0], "stream_id") else 0
        self.timestamp: float = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.events, self.timestamp

    def set_state(self, state):
        self.from_client, self.events, self.timestamp = state

    def __repr__(self):
        return "<HTTP2Frame: {direction}, type: {type}, events: {events}>".format(
            direction="->" if self.from_client else "<-",
            type=self.frame_type,
            events=repr(self.events)
        )

    def _detect_frame_type(self, event: events.Event) -> str:
        if isinstance(event, events.RequestReceived):
            return "HEADER"
        elif isinstance(event, events.ResponseReceived):
            return "HEADER"
        elif isinstance(event, events.TrailersReceived):
            raise "TRAILER RECEIVED"
        elif isinstance(event, events.InformationalResponseReceived):
            raise "INFORMATIONAL RESPONSE RECEIVED"
        elif isinstance(event, events.DataReceived):
            return "DATA"
        elif isinstance(event, events.WindowUpdated):
            return "WINDOWS UPDATE"
        elif isinstance(event, events.RemoteSettingsChanged):
            return "SETTINGS"
        elif isinstance(event, events.PingReceived):
            return "PING"
        elif isinstance(event, events.PingAcknowledged):
            return "PING"
        elif isinstance(event, events.StreamReset):
            return "STREAM RESET"
        elif isinstance(event, events.PushedStreamReceived):
            return "PUSH"
        elif isinstance(event, events.SettingsAcknowledged):
            return "SETTINGS"
        elif isinstance(event, events.PriorityUpdated):
            return "PRIORITY"
        elif isinstance(event, events.ConnectionTerminated):
            return "CONNECTION TERMINATED"
        elif isinstance(event, events.AlternativeServiceAvailable):
            return "ALTSVC"
        elif isinstance(event, events.UnknownFrameReceived):
            return "UNKNOWN"
        else:
            return "UNKNOWN"

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
