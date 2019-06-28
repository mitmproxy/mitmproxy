from mitmproxy import flow
from mitmproxy import controller
from mitmproxy import viewitem
from mitmproxy.coretypes import callbackdict
import time
from typing import List
import typing

import h2.events
from h2.errors import ErrorCodes
from h2.settings import SettingCodes, ChangedSetting
from hpack.hpack import HeaderTuple


class _EndStreamFrame():

    """
        Used for all frame type which can have the "end stream" flags
    """

    def __init__(self, end_stream):
        self._end_stream: bool = end_stream

    @property
    def end_stream(self):
        return self._end_stream

    @end_stream.setter
    def end_stream(self, end_stream: bool):
        if self._events:
            if end_stream and not self._stream_id:
                new_event = h2.events.StreamEnded()
                new_event.stream_id = self._stream_id
                for event in self._events:
                    if hasattr(event, "stream_ended"):
                        event = new_event
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
        self._priority: callbackdict.CallbackDict[str, typing.Any] = callbackdict.CallbackDict(priority)
        self._priority.callback = self._update_priority

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, priority: callbackdict.CallbackDict):
        if self._events:
            if priority and not self._priority:
                new_event = h2.events.PriorityUpdated()
                new_event.stream_id = self._stream_id

                for event in self._events:
                    if hasattr(event, "priority_updated"):
                        event = new_event
                self._events.append(new_event)
            elif not priority:
                for event in self._events:
                    if hasattr(event, "priority_updated"):
                        event.priority_updated = None
                    elif isinstance(event, h2.events.PriorityUpdated):
                        self._events.remove(event)
        self._priority = callbackdict.CallbackDict(priority)
        self._priority.callback = self._update_priority
        self._update_priority()

    def _update_priority(self):
        if self._events:
            for event in self._events:
                if isinstance(event, h2.events.PriorityUpdated):
                    event.weight = self._priority['weight']
                    event.depends_on = self._priority['depends_on']
                    event.exclusive = self._priority['exclusive']


class HTTP2Frame(viewitem.ViewItem):

    """
    This is a class to represent a frame
    """

    def __init__(self, from_client, flow=None, events=[], stream_id=0, timestamp=None):
        viewitem.ViewItem.__init__(self, flow)
        self.frame_type = "UNKNOWN"
        self.from_client: bool = from_client
        self.flow_id = flow.id if flow else None
        self._stream_id: int = stream_id
        # Used to be able to update the events if the user or an addon modified this frame
        # Note that this reference is ONLY available in live
        # When we restore all flow (from a file), this reference contains only an empty list
        self._events: List[h2.events.Event] = events
        self.timestamp: float = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        # Note that the serialization mecanisme don't support inheritance
        # The type of the serialized object defined staticly by the type defined in "_stateobject_attributes"
        # To be able to use a subclass for the frames we store the type of the frame when we serialize the objet
        # When we restore the object we need to call the "from_state" method of the subclass
        cls = eval(state.pop('frame_class'))
        args = dict(from_client=state['from_client'],
                    stream_id=state['_stream_id'],
                    timestamp=state['timestamp'])
        return cls.from_state(state, args)

    def copy(self):
        f = super().copy()
        f.flow = self.flow
        self.flow.messages.append(f)
        if self.flow.reply is not None:
            f.flow.reply = controller.DummyReply()
        return f

    def set_state(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        # Save the type of the classe to be able to restore the good classe type
        state['frame_class'] = type(self).__name__
        # Remove the flow reference
        # Note that this reference is restaured by the master in the "load_flow" process
        del state["flow"]
        # Remove the event reference. It's not usefull if we are not in live
        del state["_events"]
        return state

    # Frame property
    @property
    def stream_id(self):
        return self._stream_id

    @stream_id.setter
    def stream_id(self, stream_id: int):
        self._stream_id = stream_id
        if self._events:
            for event in self._events:
                if hasattr(event, "stream_id"):
                    event.stream_id = stream_id

    def __repr__(self):
        return "<HTTP2Frame: {direction}, stream ID: {stream_id}>".format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id)


class Http2Header(HTTP2Frame, _EndStreamFrame, _PriorityFrame):

    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client, headers, hpack_info, priority, end_stream, flow=None, events=[], stream_id=0, timestamp=None):
        HTTP2Frame.__init__(self, from_client, flow, events, stream_id, timestamp)
        _EndStreamFrame.__init__(self, end_stream)
        self.frame_type = "HEADER"
        if priority:
            _PriorityFrame.__init__(self, priority)
        else:
            self._priority = None
        self._headers: HeaderTuple = headers
        self.hpack_info = hpack_info

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Header(**args, headers=state['_headers'], hpack_info=state['hpack_info'],
                           priority=state['_priority'], end_stream=state['_end_stream'])

    def get_state(self):
        state = HTTP2Frame.get_state(self)
        state['_headers'] = list(self._headers)
        state['hpack_info']['dynamic'] = list(self.hpack_info['dynamic'])
        hpack_dynamic = state['hpack_info']['dynamic']
        # Note that sometime we get a memoryview object type in the hpack tuple
        # so convert it to a type which is serializable
        for index in range(0, len(hpack_dynamic)):
            if isinstance(hpack_dynamic[index][0], memoryview):
                hpack_dynamic[index] = hpack_dynamic[index][0].tobytes(), hpack_dynamic[index][1]
            if isinstance(hpack_dynamic[index][1], memoryview):
                hpack_dynamic[index] = hpack_dynamic[index][0], hpack_dynamic[index][1].tobytes()
        return state

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTuple):
        self._headers = headers
        if self._events:
            for event in self._events:
                if hasattr(event, "headers"):
                    event.headers = headers

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame HEADER: {direction}, stream ID: {stream_id}, "
                "headers = {headers}, priority: {priority}, end_stream = {end_stream}>").format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            priority=self._priority,
            headers=self._headers,
            end_stream=self.end_stream)


class Http2Push(HTTP2Frame):

    """
    This is a class to represent a HEADER frame
    """

    def __init__(self, from_client, pushed_stream_id, headers, hpack_info, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, stream_id, timestamp)
        self.frame_type = "PUSH PROMISE"
        self._pushed_stream_id: int = pushed_stream_id
        self._headers: HeaderTuple = headers
        self.hpack_info = hpack_info

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Push(**args, pushed_stream_id=state['_pushed_stream_id'], headers=state['_headers'], hpack_info=state['hpack_info'])

    def get_state(self):
        state = HTTP2Frame.get_state(self)
        state['_headers'] = list(self._headers)
        state['hpack_info']['dynamic'] = list(self.hpack_info['dynamic'])
        hpack_dynamic = state['hpack_info']['dynamic']
        # Note that sometime we get a memoryview object type in the hpack tuple
        # so convert it to a type which is serializable
        for index in range(0, len(hpack_dynamic)):
            if isinstance(hpack_dynamic[index][0], memoryview):
                hpack_dynamic[index] = hpack_dynamic[index][0].tobytes(), hpack_dynamic[index][1]
            if isinstance(hpack_dynamic[index][1], memoryview):
                hpack_dynamic[index] = hpack_dynamic[index][0], hpack_dynamic[index][1].tobytes()
        return state

    # Frame property
    @property
    def stream_id(self):
        return self._stream_id

    @stream_id.setter
    def stream_id(self, stream_id: int):
        self._stream_id = stream_id
        if self._events:
            for event in self._events:
                if hasattr(event, "parent_stream_id"):
                    event.parent_stream_id = stream_id

    @property
    def pushed_stream_id(self):
        return self._pushed_stream_id

    @pushed_stream_id.setter
    def pushed_stream_id(self, pushed_stream_id: int):
        self._pushed_stream_id = pushed_stream_id
        if self._events:
            for event in self._events:
                if hasattr(event, "pushed_stream_id"):
                    event.pushed_stream_id = pushed_stream_id

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTuple):
        self._headers = headers
        if self._events:
            for event in self._events:
                if hasattr(event, "headers"):
                    event.headers = headers

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame PUSH PROMISE: {direction}, stream ID: {stream_id}, Headers: {headers}>".format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            headers=self._headers)


class Http2Data(HTTP2Frame, _EndStreamFrame):

    """
    This is a class to represent a DATA frame
    """

    def __init__(self, from_client, data, flow_controlled_length, end_stream, flow=None, events=[], stream_id=0, timestamp=None):
        HTTP2Frame.__init__(self, from_client, flow, events, stream_id, timestamp)
        _EndStreamFrame.__init__(self, end_stream)
        self.frame_type = "DATA"
        self._data: bytes = data
        self._length: int = flow_controlled_length

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Data(**args, data=state['_data'], flow_controlled_length=state['_length'],
                         end_stream=state['_end_stream'])

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: bytes):
        self._data = data
        if self._events:
            for event in self._events:
                if hasattr(event, "data"):
                    event.data = data

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length: int):
        self._length = length
        if self._length:
            for event in self._events:
                if hasattr(event, "flow_controlled_length"):
                    event.flow_controlled_length = length

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame DATA: {direction}, stream ID: {stream_id}, "
                "Data: {data}, Length: {length}>").format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            data=self._data,
            length=self._length)


class Http2WindowsUpdate(HTTP2Frame):

    """
    This is a class to represent a Windows Update frame
    """

    def __init__(self, from_client, delta, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, stream_id, timestamp)
        self.frame_type = "WINDOWS UPDATE"
        self._delta: int = delta

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2WindowsUpdate(**args, delta=state['_delta'])

    @property
    def delta(self):
        return self._delta

    @delta.setter
    def delta(self, delta: int):
        self._delta = delta
        if self._events:
            for event in self._events:
                if hasattr(event, "delta"):
                    event.delta = delta

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame WINDOWS UPDATE: {direction}, stream ID: {stream_id}, delta: {delta}>".format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            delta=self._delta)


class Http2Settings(HTTP2Frame):

    """
    This is a class to represent a Settings frame
    """

    def __init__(self, from_client, settings, ack, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, 0, timestamp)
        self.frame_type = "SETTINGS"
        self._ack: bool = ack
        self._settings: callbackdict.CallbackDict[int, int] = callbackdict.CallbackDict(settings)
        for k, v in self._settings.items():
            self._settings[k] = callbackdict.CallbackDict(v)
            self._settings[k].callback = self._update_settings
        self._settings.callback = self._update_settings

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Settings(**args, settings=state['_settings'], ack=state['_ack'])

    @property
    def ack(self):
        return self._ack

    @ack.setter
    def ack(self, ack: bool):
        if self._events:
            if ack != self._ack:
                if ack:
                    new_event = h2.events.SettingsAcknowledged()
                else:
                    new_event = h2.events.RemoteSettingsChanged()
                for event in self._events:
                    if isinstance(event, h2.events.SettingsAcknowledged) or isinstance(event, h2.events.RemoteSettingsChanged):
                        new_event.changed_settings = event.changed_settings
                        self._events.remove(event)
                self._events.append(new_event)
        self._ack = ack

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, settings):
        self._settings = settings
        self._update_settings()

    def _update_settings(self):
        if self._events:
            for event in self._events:
                if hasattr(event, "changed_settings"):
                    for key, setting in self._settings.items():
                        settings_key = SettingCodes(key)
                        if 'original_value' not in setting and 'new_value' not in setting:
                            raise ValueError("No settings value for key %s")
                        if 'original_value' not in setting:
                            setting['original_value'] = setting['new_value']
                        if 'new_value' not in setting:
                            setting['new_value'] = setting['original_value']
                        if settings_key not in event.changed_settings:
                            event.changed_settings[settings_key] = ChangedSetting(settings_key, setting['original_value'], setting['new_value'])
                        else:
                            event.changed_settings[settings_key].original_value = setting['original_value']
                            event.changed_settings[settings_key].new_value = setting['new_value']
                    for setting in event.changed_settings.copy().keys():
                        if int(setting) not in self._settings:
                            del event.changed_settings[setting]

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame SETTINGS: {direction}, stream ID: {stream_id}, settings: {settings}, ack: {ack}>".format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            settings=self._settings,
            ack=self._ack)


class Http2Ping(HTTP2Frame):

    """
    This is a class to represent a Ping frame
    """

    def __init__(self, from_client, data, ack, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, 0, timestamp)
        self.frame_type = "PING"
        self._data: bytes = data
        self._ack: bool = ack

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Ping(**args, data=state['_data'], ack=state['_ack'])

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: bytes):
        self._data = data
        if self._events:
            for event in self._events:
                if hasattr(event, "ping_data"):
                    event.ping_data = data

    @property
    def ack(self):
        return self._ack

    @ack.setter
    def ack(self, ack: bool):
        if self._events:
            if ack != self._ack:
                if ack:
                    new_event = h2.events.PingAckReceived()
                else:
                    new_event = h2.events.PingReceived()
                new_event.ping_data = self._data

                for event in self._events:
                    if isinstance(event, h2.events.PingAckReceived) or isinstance(event, h2.events.PingReceived):
                        self._events.remove(event)
                self._events.append(new_event)
        self._ack = ack

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return "<HTTP2Frame PING: {direction}, stream ID: {stream_id}, data: {data}, ack {ack}>".format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            data=self._data,
            ack=self._ack)


class Http2PriorityUpdate(HTTP2Frame, _PriorityFrame):

    """
    This is a class to represent a Priority update frame
    """

    def __init__(self, from_client, priority, flow=None, events=[], stream_id=0, timestamp=None):
        HTTP2Frame.__init__(self, from_client, flow, events, 0, timestamp)
        self.frame_type = "PRIORITY"
        _PriorityFrame.__init__(self, priority)

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2PriorityUpdate(**args, priority=state['_priority'])

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame PRIORITY: {direction}, stream ID: {stream_id}, "
                "weight: {weight}, depends on: {depends_on}, exclusive: {exclusive}>").format(
            direction="->" if self.from_client else "<-",
            type=repr(type(self)),
            stream_id=self._stream_id,
            weight=self._priority['weight'],
            depends_on=self._priority['depends_on'],
            exclusive=self._priority['exclusive'])


class Http2RstStream(HTTP2Frame):

    """
    This is a class to represent a Reset stream frame
    """

    def __init__(self, from_client, error_code, remote_reset, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, stream_id, timestamp)
        self.frame_type = "RESET STREAM"
        self._error_code: int = error_code
        self._remote_reset: bool = remote_reset

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2RstStream(**args, error_code=state['_error_code'], remote_reset=state['_remote_reset'])

    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, error_code: int):
        self._error_code = error_code
        if self._events:
            for event in self._events:
                if hasattr(event, "error_code"):
                    event.error_code = ErrorCodes(error_code)

    @property
    def remote_reset(self):
        return self._remote_reset

    @remote_reset.setter
    def remote_reset(self, remote_reset: bool):
        self._remote_reset = remote_reset
        if self._events:
            for event in self._events:
                if hasattr(event, "remote_reset"):
                    event.remote_reset = remote_reset

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame RESET STREAM: {direction}, stream ID: {stream_id}, "
                "error code: {error_code}, remote reset: {remote_reset}>").format(
            direction="->" if self.from_client else "<-",
            stream_id=self._stream_id,
            error_code=self._error_code,
            remote_reset=self._remote_reset)


class Http2Goaway(HTTP2Frame):

    """
    This is a class to represent a Goaway frame
    """

    def __init__(self, from_client, last_stream_id, error_code, additional_data, flow=None, events=[], stream_id=0, timestamp=None):
        super().__init__(from_client, flow, events, 0, timestamp)
        self.frame_type = "GOAWAY"
        self._last_stream_id: int = last_stream_id
        self._error_code: int = error_code
        self._additional_data = additional_data

    @classmethod
    def from_state(cls, state, args=None):
        if not args:
            return super().from_state(state)
        return Http2Goaway(**args, last_stream_id=state['_last_stream_id'],
                           error_code=state['_error_code'], additional_data=state['_additional_data'])

    @property
    def last_stream_id(self):
        return self._last_stream_id

    @last_stream_id.setter
    def last_stream_id(self, last_stream_id: int):
        self._last_stream_id = last_stream_id
        if self._events:
            for event in self._events:
                if hasattr(event, "last_stream_id"):
                    event.last_stream_id = last_stream_id

    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, error_code: int):
        self._error_code = error_code
        if self._events:
            for event in self._events:
                if hasattr(event, "error_code"):
                    event.error_code = ErrorCodes(error_code)

    @property
    def additional_data(self):
        return self._additional_data

    @additional_data.setter
    def additional_data(self, additional_data):
        self._additional_data = additional_data
        if self._events:
            for event in self._events:
                if hasattr(event, "additional_data"):
                    event.additional_data = additional_data

    def __repr__(self):
        """
        Convert this object as a string
        This make more easy to debug and give easily the possibility to see what contains this class
        """
        return ("<HTTP2Frame GOAWAY: {direction}, last stream ID: {last_stream_id}, "
                "error code: {error_code}, additional data: {additional_data}>").format(
            direction="->" if self.from_client else "<-",
            last_stream_id=self._last_stream_id,
            error_code=self._error_code,
            additional_data=self._additional_data)


def frame_from_event(from_client: bool, flow, events: h2.events.Event, http2_source_connection):
    """
    Detect the type of frame and create a frame object for the specific type
    """
    frame = None
    # We get an events list but in the reality the only really usefull object is the first event
    # The other events are also generally referenced in the attributes of the first one
    # By example the others events objects could be a priority included in the HEADER frame.
    event = events[0]
    if isinstance(event, h2.events.RequestReceived) or isinstance(event, h2.events.ResponseReceived):
        hpack_info = dict(static=http2_source_connection.decoder.header_table.STATIC_TABLE,
                          dynamic=http2_source_connection.decoder.header_table.dynamic_entries)
        frame = Http2Header(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            headers=event.headers,
            hpack_info=hpack_info,
            priority=dict(
                weight=event.priority_updated.weight,
                depends_on=event.priority_updated.depends_on,
                exclusive=event.priority_updated.exclusive) if event.priority_updated else None,
            end_stream=event.stream_ended is not None)
    elif isinstance(event, h2.events.PushedStreamReceived):
        hpack_info = dict(static=http2_source_connection.decoder.header_table.STATIC_TABLE,
                          dynamic=http2_source_connection.decoder.header_table.dynamic_entries)
        frame = Http2Push(
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
            end_stream=event.stream_ended is not None)
    elif isinstance(event, h2.events.WindowUpdated):
        frame = Http2WindowsUpdate(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            delta=event.delta)
    elif isinstance(event, h2.events.RemoteSettingsChanged) or isinstance(event, h2.events.SettingsAcknowledged):
        settings = dict()
        for key, setting in event.changed_settings.items():
            settings[int(key)] = dict(original_value=setting.original_value,
                                      new_value=setting.new_value)
        frame = Http2Settings(
            from_client=from_client,
            flow=flow,
            events=events,
            settings=settings,
            ack=isinstance(event, h2.events.SettingsAcknowledged))
    elif isinstance(event, h2.events.PingReceived):
        frame = Http2Ping(
            from_client=from_client,
            flow=flow,
            events=events,
            data=event.ping_data,
            ack=False)
    elif isinstance(event, h2.events.PingAckReceived):
        frame = Http2Ping(
            from_client=from_client,
            flow=flow,
            events=events,
            data=event.ping_data,
            ack=True)
    elif isinstance(event, h2.events.PriorityUpdated):
        frame = Http2PriorityUpdate(
            from_client=from_client,
            flow=flow,
            events=events,
            priority=dict(
                weight=event.weight,
                depends_on=event.depends_on,
                exclusive=event.exclusive))
    elif isinstance(event, h2.events.StreamReset):
        frame = Http2RstStream(
            from_client=from_client,
            flow=flow,
            events=events,
            stream_id=event.stream_id,
            error_code=int(event.error_code),
            remote_reset=event.remote_reset)
    elif isinstance(event, h2.events.ConnectionTerminated):
        frame = Http2Goaway(
            from_client=from_client,
            flow=flow,
            events=events,
            last_stream_id=event.last_stream_id,
            error_code=int(event.error_code),
            additional_data=event.additional_data)
    else:
        frame = HTTP2Frame(from_client, events=events)

    return frame


class HTTP2Flow(flow.Flow):

    """
    A HTTP2Flow is a simplified representation of a Http/2 connection
    """

    def __init__(self, client_conn, server_conn, live=None, state="start"):
        super().__init__("http2", client_conn, server_conn, live)
        self.messages: List[HTTP2Frame] = []
        self.state = state

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(dict(
        messages=List[HTTP2Frame],
        state=str
    ))

    def __repr__(self):
        return "<HTTP2Flow ({} messages)>".format(len(self.messages))
