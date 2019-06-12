import typing
from mitmproxy import flow
from mitmproxy import viewitem
from mitmproxy.coretypes import serializable
import time
from typing import List

import h2.events


class HTTP2Frame(serializable.Serializable, viewitem.ViewItem):

    def __init__(self, from_client, events=[], stream_id=0, timestamp=None):
        super().__init__()
        self.from_client: bool = from_client
        self._stream_id: int = stream_id
        self.events: List[h2.events.Event] = events
        self.timestamp: float = timestamp or time.time()

    @classmethod
    def from_event(cls, from_client: bool, source_conn, events: h2.events.Event):
        # Détect the type of frame and create a frame object for the specific type
        frame = None
        event = events[0]
        if isinstance(event, h2.events.RequestReceived) or isinstance(event, h2.events.ResponseReceived):
            frame = Http2Header(
                from_client=from_client,
                events=events,
                stream_id=event.stream_id,
                headers=event.headers,
                hpack_info=source_conn.decoder.header_table,
                priority=dict(
                    weight=event.weight,
                    depends_on=event.depends_on,
                    exclusive=event.exclusive) if event.priority else None,
                end_stream=event.stream_ended != None)
        elif isinstance(event, h2.events.PushedStreamReceived):
            frame = Http2Pushed(
                from_client=from_client,
                events=events,
                stream_id=event.parent_stream_id,
                pushed_stream_id=event.pushed_stream_id,
                headers=event.headers,
                hpack_info=source_conn.decoder.header_table)
        elif isinstance(event, h2.events.DataReceived):
            frame = Http2Data(
                from_client=from_client,
                events=events,
                stream_id=event.stream_id,
                data=data,
                flow_controlled_length=event.flow_controlled_length,
                end_stream=event.stream_ended != None)
        elif isinstance(event, h2.events.WindowUpdated):
            frame = Http2WindowsUpdate(
                from_client=from_client,
                events=events,
                stream_id=event.stream_id,
                delta=event.delta)
        elif isinstance(event, h2.events.StreamReset):
            frame = Http2RstStream(
                from_client=from_client,
                events=events,
                stream_id=event.stream_id,
                error_code=event.error_code,
                remote_reset=event.remote_reset)
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            frame = Http2Settings(
                from_client=from_client,
                events=events,
                changed_settings=event.changed_settings,
                ack=False)
        elif isinstance(event, h2.events.SettingsAcknowledged):
            frame = Http2Settings(
                from_client=from_client,
                events=events,
                changed_settings=event.changed_settings,
                ack=True)
        elif isinstance(event, h2.events.PingReceived):
            frame = Http2Ping(
                from_client=from_client,
                events=events,
                ping_data=event.ping_data,
                ack=False)
        elif isinstance(event, h2.events.PingAcknowledged):
            frame = Http2Ping(
                from_client=from_client,
                events=events,
                ping_data=event.ping_data,
                ack=True)
        elif isinstance(event, h2.events.PriorityUpdated):
            frame = Http2PriorityUpdate(
                from_client=from_client,
                events=events,
                weight=event.weight,
                depends_on=event.depends_on,
                exclusive=event.exclusive)
        else:
            frame = HTTP2Frame(from_client, events=events)

        return frame

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def set_state(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        state.remove("events")
        return state

    # Frame property
    @property
    def stream_id(self):
        return self._stream_id

    @stream_id.setter
    def stream_id(self, stream_id: int):
        self._stream_id
        for event in events:
            if hasattr(event, "stream_id"):
                event.stream_id = stream_id

    def __repr__(self):
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}>".format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=_stream_id
        )


class Http2Header(HTTP2Frame):
    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client, events, stream_id, headers, hpack_info, priority, end_stream):
        super().__init__(from_client, events, stream_id)
        self.headers : hpack.HeaderTuple = None
        self.hpack_info = hpack_info
        self.priority : dict[str, typing.Any] = priority
        self.end_stream : bool = end_stream

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame HEADER: {direction}, type: {type}, stream ID: {stream_id}, "
                "headers = {headers}, priority: end_stream = {end_stream})>").format(
            stream_id=self._stream_id,
            headers=self.headers)


class Http2Data(HTTP2Frame):
    """
    This is a class to represent a DATA frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.data : h2.events.Data = None
        self.length : int = 0

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2Data(stream ID = {stream_id})>".format(
            stream_id=self.stream_id)


class Http2WindowsUpdate(HTTP2Frame):
    """
    This is a class to represent a Windows Update frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.delta : int = 0

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2WindowsUpdate(stream ID = {stream_id}, delta = {delta})>".format(
            stream_id=self.stream_id,
            delta=self.delta)


class Http2Settings(HTTP2Frame):
    """
    This is a class to represent a Settings frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.settings : Dict[str, int] = None
        self.ack : bool = False

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2Settings(stream ID = {stream_id})>".format(
            stream_id=self.stream_id)


class Http2Ping(HTTP2Frame):
    """
    This is a class to represent a Ping frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.ping_data : h2.events.ping_data = None

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2Ping(stream ID = {stream_id})>".format(
            stream_id=self.stream_id)


class Http2Pushed(HTTP2Frame):
    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.parent_stream_id : int = 0

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2Pushed(stream ID = {stream_id}, parent stream id = {parent})>".format(
            stream_id=self.stream_id,
            parent=self.parent_stream_id)


class Http2RstStream(HTTP2Frame):
    """
    This is a class to represent a Reset stream frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.ping_data : h2.events.ping_data = None

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2RstStream(stream ID = {stream_id})>".format(
            stream_id=self.stream_id)


class Http2PriorityUpdate(HTTP2Frame):
    """
    This is a class to represent a Priority update frame
    """

    def __init__(self, from_client):
        super().__init__()
        self.weight : int = 0
        self.depends_on : int = 0

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<Http2PriorityUpdate(stream ID = {stream_id}, weight = {weight}, depends on = {depends})>".format(
            stream_id=self.stream_id,
            depends=self.depends_on,
            weight=self.weight)


class HTTP2Flow(flow.Flow):

    """
    A Http2Flow is a simplified representation of a Http/2 connection
    """

    def __init__(self, client_conn, server_conn, live=None, state="start"):
        super().__init__("http2", client_conn, server_conn, live)
        self.messages: List[Http2Frame] = []
        self.state = state

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(dict(
        messages=List[HTTP2Frame],
        state=str
    ))

    def __repr__(self):
        return "<Http2Flow ({} messages)>".format(len(self.messages))
