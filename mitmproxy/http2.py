import typing
from mitmproxy import flow
from mitmproxy import viewitem
from mitmproxy.coretypes import serializable
from mitmproxy.coretypes import callbackdict
import time
from typing import List

import h2.events
from hpack.hpack import HeaderTuple

class _EndStreamFrame():

    """
        Used for all frame type which can have the "end stream" flags
    """
    def __init__(self, end_stream):
        self._end_stream : bool = end_stream

    @property
    def end_stream(self):
        return self._end_stream

    @end_stream.setter
    def end_stream(self, end_stream: bool):
        if end_stream and not self._stream_id:
            new_event = h2.events.StreamEnded()
            new_event.stream_id = self._stream_id
            for event in self._events:
                if hasattr(event, "stream_ended"):
                    event =new_event
            self._events.append(new_event)
        elif not end_stream:
            for event in self._events:
                if hasattr(event, "stream_ended"):
                    event.stream_ended = None
                elif isinstance(event, h2.events.StreamEnded):
                    self._events.remove(event)
        self._end_stream = end_stream

class _PriorityFrame():

    """
        Used for all frame type which can have the "priority" informations
    """
    def __init__(self, priority):
        self._priority : callbackdict.CallbackDict[str, typing.Any] = priority
        priority.set_callback(self._update_priority)

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, priority: callbackdict.CallbackDict):
        if priority and not self._priority:
            new_event = h2.events.PriorityUpdated()
            new_event.stream_id = self._stream_id

            for event in self._events:
                if hasattr(event, "priority_updated"):
                    event =new_event
            self._events.append(new_event)
        elif not priority:
            for event in self._events:
                if hasattr(event, "priority_updated"):
                    event.priority_updated = None
                elif isinstance(event, h2.events.PriorityUpdated):
                    self._events.remove(event)
        self._priority = priority
        self._update_priority()

    def _update_priority(self):
        for event in self.events:
            if isinstance(event, h2.events.PriorityUpdated):
                event.weight = self._priority['weight']
                event.depends_on = self._priority['depends_on']
                event.depends_on = self._priority['exclusive']

class HTTP2Frame(serializable.Serializable, viewitem.ViewItem):

    """
    This is a class to represent a frame
    """
    def __init__(self, from_client, flow, events=[], stream_id=0, timestamp=None):
        super().__init__()
        self.from_client: bool = from_client
        self._flow: HTTP2Flow = flow
        self._stream_id: int = stream_id
        self._events: List[h2.events.Event] = events
        self.timestamp: float = timestamp or time.time()

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
        self._stream_id = stream_id
        for event in self._events:
            if hasattr(event, "stream_id"):
                event.stream_id = stream_id

    def __repr__(self):
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}>".format(
                direction="->" if self.from_client else "<-",
                type=repr(type(self)),
                stream_id=self._stream_id)


class Http2Header(HTTP2Frame, _EndStreamFrame, _PriorityFrame):

    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client, flow, events, stream_id, headers, hpack_info, priority, end_stream):
        HTTP2Frame.__init__(from_client, flow, events, stream_id)
        _EndStreamFrame.__init__(self, end_stream)
        _PriorityFrame.__init__(self, priority)
        self._headers : hpack.HeaderTuple = headers
        self.hpack_info = hpack_info

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame HEADER: {direction}, type: {type}, stream ID: {stream_id}, "
                "headers = {headers}, priority: {priority}, end_stream = {end_stream}>").format(
                direction="->" if self.from_client else "<-",
                type=repr(type(self)),
                stream_id=self._stream_id,
                priority=self._priority,
                headers=self._headers)

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTuple):
        self._headers = headers
        for event in self._events:
            if hasattr(event, "headers"):
                event.headers = headers


class Http2Data(HTTP2Frame, _EndStreamFrame):

    """
    This is a class to represent a DATA frame
    """

    def __init__(self, from_client, flow, events, stream_id, data, flow_controlled_length, end_stream):
        HTTP2Frame.__init__(self, from_client, flow, events, stream_id)
        _EndStreamFrame.__init__(self, end_stream)
        self._data : h2.events.Data = None
        self._length : int = flow_controlled_length

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame HEADER: {direction}, type: {type}, stream ID: {stream_id}, "
                "Data: {data}, Length: {length}>").format(
                direction="->" if self.from_client else "<-",
                type=repr(type(self)),
                stream_id=self._stream_id,
                data=self._data,
                length=self._length)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: bytes):
        self._data = data
        for event in self._events:
            if hasattr(event, "data"):
                event.data = data

    @property
    def length(self):
        return self._length


class Http2WindowsUpdate(HTTP2Frame):

    """
    This is a class to represent a Windows Update frame
    """

    def __init__(self, from_client, flow, events, stream_id, delta):
        super().__init__(from_client, flow, events, stream_id)
        self._delta : int = delta

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}, delta: {delta}>".format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id,
            delta=self._delta)

    @property
    def delta(self):
        return self._delta

    @delta.setter
    def delta(self, delta: int):
        self._delta = delta
        for event in self._events:
            if hasattr(event, "delta"):
                event.delta = delta


class Http2Settings(HTTP2Frame):

    """
    This is a class to represent a Settings frame
    """

    def __init__(self, from_client, flow, events, stream_id, settings):
        super().__init__(from_client, flow, events, stream_id)
        self._settings : Dict[str, int] = None
        self._ack : bool = False

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}>".format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id)

    # TODO Implement !!

class Http2Ping(HTTP2Frame):

    """
    This is a class to represent a Ping frame
    """

    def __init__(self, from_client, flow, events, stream_id, data, ack):
        super().__init__(from_client, flow, events, stream_id)
        self._data : h2.events.ping_data = data
        self._ack: bool = ack

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}, data: {data}, ack {ack}>".format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id,
            data=self._data,
            ack=self._ack)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: int):
        self._data = data
        for event in self._events:
            if hasattr(event, "ping_data"):
                event.ping_data = data

    @property
    def ack(self):
        return self._ack

    @ack.setter
    def ack(self, ack: int):
        if ack != self._ack:
            if _ack:
                new_event = h2.events.PingAckReceived()
            else:
                new_event = h2.events.PingReceived()
            new_event.ping_data = self._data

            for event in self._events:
                if isinstance(event, h2.events.PingAckReceived) or isinstance(event, h2.events.PingReceived):
                    self._events.remove(event)
            self._events.append(new_event)
        self._ack = ack


class Http2Pushed(HTTP2Frame):

    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client, flow, events, stream_id, pushed_stream_id, headers, hpack_info):
        super().__init__(from_client, flow, events, stream_id)
        self.pushed_stream_id : int = pushed_stream_id
        self._headers : hpack.HeaderTuple = headers
        self.hpack_info = hpack_info

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}, Headers: {headers}>".format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id,
            headers=self._headers)

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTuple):
        self._headers = headers
        for event in self._events:
            if hasattr(event, "headers"):
                event.headers = headers


class Http2RstStream(HTTP2Frame):

    """
    This is a class to represent a Reset stream frame
    """

    def __init__(self, from_client, flow, events, stream_id, error_code, remote_reset):
        super().__init__(from_client, flow, events, stream_id)
        self._error_code: int = error_code
        self._remote_reset: bool = remote_reset

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}, "
                "error code: {error_code}, remote reset: {remote_reset}>").format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id,
            error_code=self._error_code,
            remote_reset=self._remote_reset)

    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, error_code: int):
        self._error_code = error_code
        for event in self._events:
            if hasattr(event, "error_code"):
                event.error_code = error_code

    @property
    def remote_reset(self):
        return self._remote_reset

    @remote_reset.setter
    def remote_reset(self, remote_reset: bool):
        self._remote_reset = remote_reset
        for event in self._events:
            if hasattr(event, "remote_reset"):
                event.remote_reset = remote_reset


class Http2PriorityUpdate(HTTP2Frame, _PriorityFrame):

    """
    This is a class to represent a Priority update frame
    """

    def __init__(self, from_client, flow, events, priority):
        HTTP2Frame.__init__(self, from_client, flow, events, 0)
        _PriorityFrame.__init__(self, priority)

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame: {direction}, type: {type}, stream ID: {stream_id}, "
                "weight: {weight}, depends on: {depends_on}, exclusive: {exclusive}>").format(
                direction="->" if self.from_client else "<-",
                type=repr(type(self)),
                stream_id=self._stream_id,
                weight=self._priority['weight'],
                depends_on=self._priority['depends_on'],
                exclusive=self._priority['exclusive'])


def frame_from_event(from_client: bool, flow, events: h2.events.Event):
    # Détect the type of frame and create a frame object for the specific type
    frame = None
    event = events[0]
    if isinstance(event, h2.events.RequestReceived) or isinstance(event, h2.events.ResponseReceived):
        hpack_info = (flow.client_conn.decoder.header_table if from_client 
                      else flow.server_conn.decoder.header_table)
        frame = Http2Header(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            headers=event.headers,
            hpack_info=hpack_info,
            priority=callbackdict.CallbackDict(
                weight=event.priority.weight,
                depends_on=event.priority.depends_on,
                exclusive=event.priority.exclusive) if event.priority else None,
            end_stream=event.stream_ended != None)
    elif isinstance(event, h2.events.PushedStreamReceived):
        hpack_info = (flow.client_conn.decoder.header_table if from_client 
                      else flow.server_conn.decoder.header_table)
        frame = Http2Pushed(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.parent_stream_id,
            pushed_stream_id=event.pushed_stream_id,
            headers=event.headers,
            hpack_info=hpack_info)
    elif isinstance(event, h2.events.DataReceived):
        frame = Http2Data(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            data=event.data,
            flow_controlled_length=event.flow_controlled_length,
            end_stream=event.stream_ended != None)
    elif isinstance(event, h2.events.WindowUpdated):
        frame = Http2WindowsUpdate(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            delta=event.delta)
    elif isinstance(event, h2.events.StreamReset):
        frame = Http2RstStream(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            error_code=event.error_code,
            remote_reset=event.remote_reset)
    elif isinstance(event, h2.events.RemoteSettingsChanged):
        frame = Http2Settings(
            from_client=from_client,
            flow=flow,
            events=events,
            changed_settings=event.changed_settings,
            ack=False)
    elif isinstance(event, h2.events.SettingsAcknowledged):
        frame = Http2Settings(
            from_client=from_client,
            flow=flow,
            events=events,
            changed_settings=event.changed_settings,
            ack=True)
    elif isinstance(event, h2.events.PingReceived):
        frame = Http2Ping(
            from_client=from_client,
            flow=flow,
            events=events,
            data=event.ping_data,
            ack=False)
    elif isinstance(event, h2.events.PingAcknowledged):
        frame = Http2Ping(
            from_client=from_client,
            flow=flow,
            events=events,
            ping_data=event.ping_data,
            ack=True)
    elif isinstance(event, h2.events.PriorityUpdated):
        frame = Http2PriorityUpdate(
            from_client=from_client,
            flow=flow,
            events=events,
            priority=callbackdict.CallbackDict(
                weight=event.weight,
                depends_on=event.depends_on,
                exclusive=event.exclusive)
            weight=event.weight,
            depends_on=event.depends_on,
            exclusive=event.exclusive)
    else:
        frame = HTTP2Frame(from_client, events=events)

    return frame

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
