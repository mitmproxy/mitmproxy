from mitmproxy import flow
from mitmproxy import viewitem
from mitmproxy.coretypes import serializable
import time
from typing import List

from h2 import events


class HTTP2Frame(serializable.Serializable, viewitem.ViewItem):

    def __init__(self, from_client, events, frame_type="Unknown", stream_ID=0, timestamp=None):
        super().__init__()
        self.from_client: bool = from_client
        self.events: List[events.Event] = events
        self.frame_type: str = self._detect_frame_type(events[0]) if len(events) > 0 else "Unknown"
        self.stream_ID: int = events[0].stream_id if len(events) and hasattr(events[0], "stream_id") > 0 else 0
        self.timestamp: float = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):

        return self.from_client, [], self.frame_type, self.stream_ID, self.timestamp

    def set_state(self, state):
        from mitmproxy import ctx
        ctx.log.info("restore")
        self.from_client, event, self.frame_type, self.stream_ID, self.timestamp = state
        self.events = []
        
        

    def __repr__(self):
        return "<HTTP2Frame: {direction}, type: {type}, events: {events}>".format(
            direction="->" if self.from_client else "<-",
            type=self.frame_type,
            events=repr(self.events)
        )

    def _detect_frame_type(self, event: events.Event) -> str:
        self.content = ""
        if isinstance(event, events.RequestReceived):
            self.content = event.headers
            return "HEADER"
        elif isinstance(event, events.ResponseReceived):
            return "HEADER"
        elif isinstance(event, events.TrailersReceived):
            raise "TRAILER RECEIVED"
        elif isinstance(event, events.InformationalResponseReceived):
            raise "INFORMATIONAL RESPONSE RECEIVED"
        elif isinstance(event, events.DataReceived):
            self.content = event.data
            return "DATA"
        elif isinstance(event, events.WindowUpdated):
            return "WINDOWS UPDATE"
        elif isinstance(event, events.RemoteSettingsChanged):
            return "SETTINGS"
        elif isinstance(event, events.PingReceived):
            self.content = event.ping_data
            return "PING"
        elif isinstance(event, events.PingAcknowledged):
            return "PING"
        elif isinstance(event, events.StreamReset):
            self.error_code = event.error_code
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

    def __init__(self, client_conn, server_conn, live=None, state="start"):
        super().__init__("http2", client_conn, server_conn, live)
        self.messages: List[Http2Frame] = []
        self.state = state

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    #_stateobject_attributes["messages"] = List[HTTP2Frame]
    _stateobject_attributes.update(dict(
        messages=List[HTTP2Frame],
        state=str
    ))

    def __repr__(self):
        return "<Http2Flow ({} messages)>".format(len(self.messages))
