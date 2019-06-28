import pytest

from mitmproxy import http2
import h2
from mitmproxy.proxy.protocol.http2 import SafeH2Connection
from mitmproxy import flowfilter
from mitmproxy.test import tflow
from h2.settings import SettingCodes, ChangedSetting


class TestHTTP2Flow:

    def get_h2_connections(self, f):
        return (SafeH2Connection(
            f.server_conn,
            h2.config.H2Configuration(
                client_side=True,
                header_encoding=False,
                validate_outbound_headers=False,
                validate_inbound_headers=False)),
                SafeH2Connection(
            f.client_conn,
            h2.config.H2Configuration(
                client_side=False,
                header_encoding=False,
                validate_outbound_headers=False,
                validate_inbound_headers=False)))

    def check_stream_id(self, frame):
        frame.stream_id = 3
        assert frame.stream_id == 3
        for e in frame._events:
            if hasattr(e, "stream_id"):
                assert e.stream_id == 3

    def test_copy(self):
        f = tflow.thttp2flow()
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]

        for i in range(0, len(a['messages'])):
            del a['messages'][i]['id']
            del a['messages'][i]['flow_id']
            del b['messages'][i]['id']
            del b['messages'][i]['flow_id']

        assert a == b
        assert not f == f2
        assert f is not f2

        assert f.messages is not f2.messages

        # We need to make a copy because when we copy a message, it's added to the messages list of the flow
        for m in f.messages.copy():
            assert m.get_state()
            m2 = m.copy()
            assert not m == m2
            assert m is not m2

            a = m.get_state()
            b = m2.get_state()
            del a['id']
            del a['flow_id']
            del b['id']
            del b['flow_id']
            assert a == b

        m = http2.HTTP2Frame(False, f)
        m.set_state(f.messages[0].get_state())
        assert m.timestamp == f.messages[0].timestamp

        f = tflow.thttp2flow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    # TODO
    # def test_match(self):
        #f = tflow.thttp2flow()
        #assert not flowfilter.match("~b nonexistent", f)
        #assert flowfilter.match(None, f)
        #assert not flowfilter.match("~b nonexistent", f)

        #f = tflow.thttp2flow(err=True)
        #assert flowfilter.match("~e", f)

        # with pytest.raises(ValueError):
        #flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.thttp2flow()
        assert 'HTTP2Flow' in repr(f)
        assert '->' in repr(f.messages[0])
        for frame in f.messages:
            assert frame.frame_type in repr(frame)

    # Tests each frames
    def test_frames_headers(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.RequestReceived()
        event.stream_id = 10
        event.headers = [(b':method', b'GET'),
                         (b':path', b'/?q=&t=h_'),
                         (b':scheme', b'https'),
                         (b'accept', memoryview(b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')),
                         (b'accept-encoding', b'gzip, deflate, br'),
                         (memoryview(b'upgrade-insecure-requests'), b'1'),
                         (b'cache-control', b'max-age=0'),
                         (b'te', b'trailers')]
        frame = http2.frame_from_event(True, f, [event], connC)

        self.check_stream_id(frame)

        event = h2.events.ResponseReceived()
        event.stream_id = 10
        event.headers = [(b':status', b'200'),
                         (b'server', b'nginx'),
                         (b'content-type', b'text/html; charset=UTF-8'),
                         (b'vary', b'Accept-Encoding'),
                         (b'strict-transport-security', b'max-age=31536000'),
                         (b'x-frame-options', memoryview(b'SAMEORIGIN')),
                         (memoryview(b'x-content-type-options'), b'nosniff'),
                         (b'referrer-policy', b'origin')]
        frame = http2.frame_from_event(True, f, [event], connS)

        self.check_stream_id(frame)
        frame.headers = [(b':status', b'400'), (b'server', b'apache')]
        assert frame.headers == [(b':status', b'400'), (b'server', b'apache')]
        assert event.headers == [(b':status', b'400'), (b'server', b'apache')]

        # TODO check priority

    def test_frames_push(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.PushedStreamReceived()
        event.pushed_stream_id = 4
        event.parent_stream_id = 6
        event.headers = [(b':method', b'GET'),
                         (b':path', b'/?q=&t=h_'),
                         (b':scheme', b'https'),
                         (b'accept', b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                         (b'accept-encoding', b'gzip, deflate, br'),
                         (b'upgrade-insecure-requests', b'1'),
                         (b'cache-control', b'max-age=0'),
                         (b'te', b'trailers')]
        frame = http2.frame_from_event(True, f, [event], connS)

        frame.stream_id = 8
        frame.pushed_stream_id = 10
        frame.headers = [(b':status', b'400'), (b'server', b'apache')]
        assert frame.stream_id == 8
        assert event.parent_stream_id == 8
        assert frame.pushed_stream_id == 10
        assert event.pushed_stream_id == 10
        assert frame.headers == [(b':status', b'400'), (b'server', b'apache')]
        assert event.headers == [(b':status', b'400'), (b'server', b'apache')]

    def test_frames_data(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.DataReceived()
        event.stream_id = 10
        event.data = b'Hello'
        event.flow_controlled_length = 120
        event.stream_ended = h2.events.StreamEnded()
        event.stream_ended.stream_id = 10
        frame = http2.frame_from_event(True, f, [event, event.stream_ended], connS)

        self.check_stream_id(frame)

        frame.data = b'I\'ve changed'
        frame.length = 2
        assert frame.data == b'I\'ve changed'
        assert event.data == b'I\'ve changed'
        assert frame.length == 2
        assert event.flow_controlled_length == 2

    def test_frames_windows_update(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.WindowUpdated()
        event.stream_id = 3
        event.delta = 12919
        frame = http2.frame_from_event(True, f, [event], connC)

        self.check_stream_id(frame)

        frame.delta = 1111
        assert frame.delta == 1111
        assert event.delta == 1111

    def test_frames_settings(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.RemoteSettingsChanged()
        event.changed_settings = {
            SettingCodes.HEADER_TABLE_SIZE: ChangedSetting(setting=SettingCodes.HEADER_TABLE_SIZE,
                                                           original_value=4096, new_value=65536),
            SettingCodes.INITIAL_WINDOW_SIZE: ChangedSetting(setting=SettingCodes.INITIAL_WINDOW_SIZE,
                                                             original_value=65535, new_value=131072),
            SettingCodes.MAX_FRAME_SIZE: ChangedSetting(setting=SettingCodes.MAX_FRAME_SIZE,
                                                        original_value=16384, new_value=16385)}
        events = [event]
        frame = http2.frame_from_event(True, f, events, connC)

        frame.ack = True
        assert frame.ack == True
        assert isinstance(events[0], h2.events.SettingsAcknowledged)

        # Check initial values
        assert frame.settings[int(SettingCodes.HEADER_TABLE_SIZE)]['original_value'] == 4096
        assert frame.settings[int(SettingCodes.HEADER_TABLE_SIZE)]['new_value'] == 65536
        assert frame.settings[int(SettingCodes.INITIAL_WINDOW_SIZE)]['original_value'] == 65535
        assert frame.settings[int(SettingCodes.INITIAL_WINDOW_SIZE)]['new_value'] == 131072
        assert frame.settings[int(SettingCodes.MAX_FRAME_SIZE)]['original_value'] == 16384
        assert frame.settings[int(SettingCodes.MAX_FRAME_SIZE)]['new_value'] == 16385

        assert events[0].changed_settings[SettingCodes.HEADER_TABLE_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.HEADER_TABLE_SIZE,
            original_value=4096, new_value=65536).__dict__
        assert events[0].changed_settings[SettingCodes.INITIAL_WINDOW_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.INITIAL_WINDOW_SIZE,
            original_value=65535, new_value=131072).__dict__
        assert events[0].changed_settings[SettingCodes.MAX_FRAME_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.MAX_FRAME_SIZE,
            original_value=16384, new_value=16385).__dict__

        # Update settings
        frame.settings[int(SettingCodes.MAX_HEADER_LIST_SIZE)] = dict(original_value=10101, new_value=1229)
        frame.settings[int(SettingCodes.MAX_CONCURRENT_STREAMS)] = dict(original_value=1111)
        frame.settings[int(SettingCodes.ENABLE_CONNECT_PROTOCOL)] = dict(new_value=201)
        frame.settings[int(SettingCodes.MAX_FRAME_SIZE)]['new_value'] = 13919
        del frame.settings[int(SettingCodes.INITIAL_WINDOW_SIZE)]

        # Tests new values
        assert frame.settings[int(SettingCodes.HEADER_TABLE_SIZE)]['original_value'] == 4096
        assert frame.settings[int(SettingCodes.HEADER_TABLE_SIZE)]['new_value'] == 65536
        assert int(SettingCodes.INITIAL_WINDOW_SIZE) not in frame.settings
        assert frame.settings[int(SettingCodes.MAX_FRAME_SIZE)]['original_value'] == 16384
        assert frame.settings[int(SettingCodes.MAX_FRAME_SIZE)]['new_value'] == 13919

        assert frame.settings[int(SettingCodes.MAX_HEADER_LIST_SIZE)]['original_value'] == 10101
        assert frame.settings[int(SettingCodes.MAX_HEADER_LIST_SIZE)]['new_value'] == 1229
        assert frame.settings[int(SettingCodes.MAX_CONCURRENT_STREAMS)]['original_value'] == 1111
        assert frame.settings[int(SettingCodes.MAX_CONCURRENT_STREAMS)]['new_value'] == 1111
        assert frame.settings[int(SettingCodes.ENABLE_CONNECT_PROTOCOL)]['original_value'] == 201
        assert frame.settings[int(SettingCodes.ENABLE_CONNECT_PROTOCOL)]['new_value'] == 201

        # Check event upgraded
        assert events[0].changed_settings[SettingCodes.HEADER_TABLE_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.HEADER_TABLE_SIZE,
            original_value=4096, new_value=65536).__dict__
        assert SettingCodes.INITIAL_WINDOW_SIZE not in events[0].changed_settings
        assert events[0].changed_settings[SettingCodes.MAX_FRAME_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.MAX_FRAME_SIZE,
            original_value=16384, new_value=13919).__dict__

        assert events[0].changed_settings[SettingCodes.MAX_HEADER_LIST_SIZE].__dict__ == ChangedSetting(
            setting=SettingCodes.MAX_HEADER_LIST_SIZE,
            original_value=10101, new_value=1229).__dict__
        assert events[0].changed_settings[SettingCodes.MAX_CONCURRENT_STREAMS].__dict__ == ChangedSetting(
            setting=SettingCodes.MAX_CONCURRENT_STREAMS,
            original_value=1111, new_value=1111).__dict__
        assert events[0].changed_settings[SettingCodes.ENABLE_CONNECT_PROTOCOL].__dict__ == ChangedSetting(
            setting=SettingCodes.ENABLE_CONNECT_PROTOCOL,
            original_value=201, new_value=201).__dict__

        with pytest.raises(ValueError, match="No settings value for key"):
            frame.settings[int(SettingCodes.ENABLE_CONNECT_PROTOCOL)] = dict(bad_key=0)

        event = h2.events.SettingsAcknowledged()
        event.changed_settings = {
            SettingCodes.HEADER_TABLE_SIZE: ChangedSetting(setting=SettingCodes.HEADER_TABLE_SIZE,
                                                           original_value=4096, new_value=65536),
            SettingCodes.INITIAL_WINDOW_SIZE: ChangedSetting(setting=SettingCodes.INITIAL_WINDOW_SIZE,
                                                             original_value=65535, new_value=131072),
            SettingCodes.MAX_FRAME_SIZE: ChangedSetting(setting=SettingCodes.MAX_FRAME_SIZE,
                                                        original_value=16384, new_value=16384)}
        events = [event]
        frame = http2.frame_from_event(True, f, events, connS)

        frame.ack = False
        assert frame.ack == False
        assert isinstance(events[0], h2.events.RemoteSettingsChanged)

    def test_frames_ping(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.PingReceived()
        event.ping_data = b'ping'
        events = [event]
        frame = http2.frame_from_event(True, f, events, connC)

        frame.data = b'hello'
        assert frame.data == b'hello'
        assert event.ping_data == b'hello'

        frame.ack = True
        assert frame.ack == True
        assert isinstance(events[0], h2.events.PingAckReceived)

        event = h2.events.PingAckReceived()
        event.ping_data = b'pong'
        events = [event]
        frame = http2.frame_from_event(True, f, events, connS)

        frame.ack = False
        assert frame.ack == False
        assert isinstance(events[0], h2.events.PingReceived)

    def test_frames_priority(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.PriorityUpdated()
        event.stream_id = 14
        event.weight = 1298
        event.depends_on = 18
        event.exclusive = True
        frame = http2.frame_from_event(True, f, [event], connC)

        self.check_stream_id(frame)
        frame.priority = dict(weight=600,
                              depends_on=28,
                              exclusive=False)

        assert frame.priority['weight'] == 600
        assert frame.priority['depends_on'] == 28
        assert frame.priority['exclusive'] == False
        assert event.weight == 600
        assert event.depends_on == 28
        assert event.exclusive == False

        frame.priority['weight'] = 50
        frame.priority['depends_on'] = 39
        frame.priority['exclusive'] = True

        assert frame.priority['weight'] == 50
        assert frame.priority['depends_on'] == 39
        assert frame.priority['exclusive'] == True
        assert event.weight == 50
        assert event.depends_on == 39
        assert event.exclusive == True

    def test_frames_reset_stream(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.StreamReset()
        event.stream_id = 12
        event.error_code = 15
        event.remote_reset = True
        frame = http2.frame_from_event(True, f, [event], connC)

        self.check_stream_id(frame)

        frame.error_code = 7
        frame.remote_reset = False
        assert frame.error_code == 7
        assert frame.remote_reset == False
        assert event.error_code == 7
        assert event.remote_reset == False

    def test_frames_connection_terminated(self):
        f = tflow.thttp2flow()
        connS, connC = self.get_h2_connections(f)

        event = h2.events.ConnectionTerminated()
        event.error_code = 13
        event.last_stream_id = 15
        event.additional_data = b'sdf'
        frame = http2.frame_from_event(True, f, [event], connC)

        frame.error_code = 7
        frame.last_stream_id = 40
        frame.additional_data = b'asdfasdf'
        assert frame.error_code == 7
        assert frame.last_stream_id == 40
        assert frame.additional_data == b'asdfasdf'
        assert event.error_code == 7
        assert event.last_stream_id == 40
        assert event.additional_data == b'asdfasdf'
