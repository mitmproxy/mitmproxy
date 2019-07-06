# coding=utf-8


import os
import tempfile
import traceback
import pytest
import h2

from mitmproxy import options

import mitmproxy.net
from ...net import tservers as net_tservers
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import http2 as http2_flow
from mitmproxy.net.http import http1, http2
from pathod.language import generators

from ... import tservers

import logging
logging.getLogger("hyper.packages.hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)
logging.getLogger("passlib.registry").setLevel(logging.WARNING)


# inspect the log:
#   for msg in self.proxy.tmaster.tlog:
#       print(msg)


class _Http2ServerBase(net_tservers.ServerTestBase):
    ssl = dict(alpn_select=b'h2')

    class handler(mitmproxy.net.tcp.BaseHandler):

        def handle(self):
            config = h2.config.H2Configuration(
                client_side=False,
                validate_outbound_headers=False,
                validate_inbound_headers=False)
            h2_conn = h2.connection.H2Connection(config)

            preamble = self.rfile.read(24)
            h2_conn.initiate_connection()
            h2_conn.receive_data(preamble)
            self.wfile.write(h2_conn.data_to_send())
            self.wfile.flush()

            if 'h2_server_settings' in self.kwargs:
                h2_conn.update_settings(self.kwargs['h2_server_settings'])
                self.wfile.write(h2_conn.data_to_send())
                self.wfile.flush()

            done = False
            while not done:
                try:
                    raw = b''.join(http2.read_raw_frame(self.rfile))
                    events = h2_conn.receive_data(raw)
                except exceptions.HttpException:
                    print(traceback.format_exc())
                    assert False
                except exceptions.TcpDisconnect:
                    break
                except:
                    print(traceback.format_exc())
                    break
                self.wfile.write(h2_conn.data_to_send())
                self.wfile.flush()

                for event in events:
                    try:
                        if not self.server.handle_server_event(event, h2_conn, self.rfile, self.wfile):
                            done = True
                            break
                    except exceptions.TcpDisconnect:
                        done = True
                    except:
                        done = True
                        print(traceback.format_exc())
                        break

    def handle_server_event(self, event, h2_conn, rfile, wfile):
        raise NotImplementedError()


class _Http2TestBase:

    @classmethod
    def setup_class(cls):
        cls.options = cls.get_options()
        cls.proxy = tservers.ProxyThread(tservers.TestMaster, cls.options)
        cls.proxy.start()

    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()

    @classmethod
    def get_options(cls):
        opts = options.Options(
            listen_port=0,
            upstream_cert=True,
            ssl_insecure=True
        )
        opts.confdir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return opts

    @property
    def master(self):
        return self.proxy.tmaster

    def setup(self):
        self.master.reset([])
        self.server.server.handle_server_event = self.handle_server_event

    def teardown(self):
        if self.client:
            self.client.close()
        self.server.server.wait_for_silence()

    def setup_connection(self):
        self.client = mitmproxy.net.tcp.TCPClient(("127.0.0.1", self.proxy.port))
        self.client.connect()

        # send CONNECT request
        self.client.wfile.write(http1.assemble_request(mitmproxy.net.http.Request(
            'authority',
            b'CONNECT',
            b'',
            b'localhost',
            self.server.server.address[1],
            b'/',
            b'HTTP/1.1',
            [(b'host', b'localhost:%d' % self.server.server.address[1])],
            b'',
        )))
        self.client.wfile.flush()

        # read CONNECT response
        while self.client.rfile.readline() != b"\r\n":
            pass

        self.client.convert_to_tls(alpn_protos=[b'h2'])

        config = h2.config.H2Configuration(
            client_side=True,
            validate_outbound_headers=False,
            validate_inbound_headers=False)
        h2_conn = h2.connection.H2Connection(config)
        h2_conn.initiate_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        return h2_conn

    def _send_request(self,
                      wfile,
                      h2_conn,
                      stream_id=1,
                      headers=None,
                      body=b'',
                      end_stream=None,
                      priority_exclusive=None,
                      priority_depends_on=None,
                      priority_weight=None,
                      streaming=False):
        if headers is None:
            headers = []
        if end_stream is None:
            end_stream = (len(body) == 0)

        h2_conn.send_headers(
            stream_id=stream_id,
            headers=headers,
            end_stream=end_stream,
            priority_exclusive=priority_exclusive,
            priority_depends_on=priority_depends_on,
            priority_weight=priority_weight,
        )
        if body:
            h2_conn.send_data(stream_id, body)
            if not streaming:
                h2_conn.end_stream(stream_id)
        wfile.write(h2_conn.data_to_send())
        wfile.flush()


class _Http2Test(_Http2TestBase, _Http2ServerBase):

    @classmethod
    def setup_class(cls):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class()

    @classmethod
    def teardown_class(cls):
        _Http2TestBase.teardown_class()
        _Http2ServerBase.teardown_class()


class TestSimple(_Http2Test):
    request_body_buffer = b''

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            assert (b'self.client-foo', b'self.client-bar-1') in event.headers
            assert (b'self.client-foo', b'self.client-bar-2') in event.headers
        elif isinstance(event, h2.events.StreamEnded):
            import warnings
            with warnings.catch_warnings():
                # Ignore UnicodeWarning:
                # h2/utilities.py:64: UnicodeWarning: Unicode equal comparison
                # failed to convert both arguments to Unicode - interpreting
                # them as being unequal.
                #     elif header[0] in (b'cookie', u'cookie') and len(header[1]) < 20:

                warnings.simplefilter("ignore")
                h2_conn.send_headers(event.stream_id, [
                    (':status', '200'),
                    ('server-foo', 'server-bar'),
                    ('föo', 'bär'),
                    ('X-Stream-ID', str(event.stream_id)),
                ])
            h2_conn.send_data(event.stream_id, b'response body')
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        elif isinstance(event, h2.events.DataReceived):
            cls.request_body_buffer += event.data
        return True

    def test_simple(self):
        response_body_buffer = b''
        h2_conn = self.setup_connection()

        headers_sent = [
            (b':authority', bytes("127.0.0.1:{}".format(self.server.server.address[1]), 'utf-8')),
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':path', b'/'),
            (b'self.client-FoO', b'self.client-bar-1'),
            (b'self.client-FoO', b'self.client-bar-2'),
        ]

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=headers_sent,
            body=b'request body')

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.DataReceived):
                    response_body_buffer += event.data
                elif isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        frames = self.master.state.flows[0].messages
        is_first_header = True
        is_first_response = True
        data_cnt = dict(client=0, server=0)
        settings_cnt = dict(client=0, client_ack=0,
                            server=0, server_ack=0)
        for f in frames:
            if isinstance(f, http2_flow.Http2Header):
                if is_first_header:
                    is_first_header = False
                    # Replace "FoO" by "Foo" because the don't do the difference between uper and lower case
                    headers_sent[4] = (b'self.client-foo', b'self.client-bar-1')
                    headers_sent[5] = (b'self.client-foo', b'self.client-bar-2')
                    assert f.headers == headers_sent
                    assert f.from_client is True
                elif is_first_response:
                    is_first_response = False
                    assert f.headers == [
                        (b':status', b'200'),
                        (b'server-foo', b'server-bar'),
                        (bytes('föo', 'utf-8'), bytes('bär', 'utf-8')),
                        (b'x-stream-id', bytes(str(event.stream_id), 'utf-8')),
                    ]
                    assert f.from_client is False
            if isinstance(f, http2_flow.Http2Data):
                if f.from_client:
                    data_cnt["client"] += 1
                    if f.end_stream:
                        assert f.data == b''
                        assert f.length == 0
                    else:
                        assert f.data == b'request body'
                        assert f.length == len(b'request body')
                else:
                    data_cnt["server"] += 1
                    if f.end_stream:
                        assert f.data == b''
                        assert f.length == 0
                    else:
                        assert f.data == b'response body'
                        assert f.length == len(b'response_body')
            if isinstance(f, http2_flow.Http2Settings):
                assert f.stream_id == 0
                if f.from_client and not f.ack:
                    settings_cnt["client"] += 1
                elif f.from_client and f.ack:
                    settings_cnt["client_ack"] += 1
                elif not f.from_client and not f.ack:
                    settings_cnt["server"] += 1
                elif not f.from_client and f.ack:
                    settings_cnt["server_ack"] += 1

        assert not is_first_header
        assert data_cnt == dict(server=2, client=2)
        assert settings_cnt == dict(client=1, client_ack=2, server=1, server_ack=2)

        assert len(self.master.state.flows) == 2
        assert self.master.state.flows[1].response.status_code == 200
        assert self.master.state.flows[1].response.headers['server-foo'] == 'server-bar'
        assert self.master.state.flows[1].response.headers['föo'] == 'bär'
        assert self.master.state.flows[1].response.content == b'response body'
        assert self.request_body_buffer == b'request body'
        assert response_body_buffer == b'response body'


class TestRequestWithPriority(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            import warnings
            with warnings.catch_warnings():
                # Ignore UnicodeWarning:
                # h2/utilities.py:64: UnicodeWarning: Unicode equal comparison
                # failed to convert both arguments to Unicode - interpreting
                # them as being unequal.
                #     elif header[0] in (b'cookie', u'cookie') and len(header[1]) < 20:

                warnings.simplefilter("ignore")

                headers = [(':status', '200')]
                if event.priority_updated:
                    headers.append(('priority_exclusive', str(event.priority_updated.exclusive).encode()))
                    headers.append(('priority_depends_on', str(event.priority_updated.depends_on).encode()))
                    headers.append(('priority_weight', str(event.priority_updated.weight).encode()))
                h2_conn.send_headers(event.stream_id, headers)
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    @pytest.mark.parametrize("http2_priority_enabled, priority, expected_priority", [
        (True, (True, 42424242, 42), ('True', '42424242', '42')),
        (False, (True, 42424242, 42), (None, None, None)),
        (True, (None, None, None), (None, None, None)),
        (False, (None, None, None), (None, None, None)),
    ])
    def test_request_with_priority(self, http2_priority_enabled, priority, expected_priority):
        self.options.http2_priority = http2_priority_enabled

        h2_conn = self.setup_connection()

        headers_sent = [
            (b':authority', bytes("127.0.0.1:{}".format(self.server.server.address[1]), 'utf-8')),
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':path', b'/'),
        ]

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=headers_sent,
            priority_exclusive=priority[0],
            priority_depends_on=priority[1],
            priority_weight=priority[2],
        )

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        assert len(self.master.state.flows) == 2

        frames = self.master.state.flows[0].messages
        priority_cnt = 0
        header_end_stream = 0
        data_cnt = 0
        is_first_header = True
        for f in frames:
            if isinstance(f, http2_flow.Http2Header):
                if f.priority:
                    priority_cnt += 1
                    assert f.priority["weight"] == priority[2]
                    assert f.priority["depends_on"] == priority[1]
                    assert f.priority["exclusive"] == priority[0]
                if f.end_stream:
                    header_end_stream += 1
                if is_first_header:
                    is_first_header = False
                    assert f.headers == headers_sent
            if isinstance(f, http2_flow.Http2Data):
                data_cnt += 1
            if isinstance(f, http2_flow.Http2PriorityUpdate):
                priority_cnt += 1
                assert f.priority["weight"] == priority[2]
                assert f.priority["depends_on"] == priority[1]
                assert f.priority["exclusive"] == priority[0]

        if priority[0]:
            assert priority_cnt == 1
        else:
            assert priority_cnt == 0
        assert header_end_stream == 1
        assert data_cnt == 1
        assert not is_first_header

        assert isinstance(frames[0], http2_flow.Http2Settings)

        resp = self.master.state.flows[1].response
        assert resp.headers.get('priority_exclusive', None) == expected_priority[0]
        assert resp.headers.get('priority_depends_on', None) == expected_priority[1]
        assert resp.headers.get('priority_weight', None) == expected_priority[2]


class TestPriority(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.PriorityUpdated):
            cls.priority_data.append((event.exclusive, event.depends_on, event.weight))
        elif isinstance(event, h2.events.RequestReceived):
            import warnings
            with warnings.catch_warnings():
                # Ignore UnicodeWarning:
                # h2/utilities.py:64: UnicodeWarning: Unicode equal comparison
                # failed to convert both arguments to Unicode - interpreting
                # them as being unequal.
                #     elif header[0] in (b'cookie', u'cookie') and len(header[1]) < 20:

                warnings.simplefilter("ignore")

                headers = [(':status', '200')]
                h2_conn.send_headers(event.stream_id, headers)
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    @pytest.mark.parametrize("prioritize_before", [True, False])
    @pytest.mark.parametrize("http2_priority_enabled, priority, expected_priority", [
        (True, (True, 42424242, 42), [(True, 42424242, 42)]),
        (False, (True, 42424242, 42), []),
    ])
    def test_priority(self, prioritize_before, http2_priority_enabled, priority, expected_priority):
        self.options.http2_priority = http2_priority_enabled
        self.__class__.priority_data = []

        h2_conn = self.setup_connection()

        if prioritize_before:
            h2_conn.prioritize(1, exclusive=priority[0], depends_on=priority[1], weight=priority[2])
            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            end_stream=prioritize_before,
        )

        if not prioritize_before:
            h2_conn.prioritize(1, exclusive=priority[0], depends_on=priority[1], weight=priority[2])
            h2_conn.end_stream(1)
            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        frames = self.master.state.flows[0].messages
        priority_cnt = 0
        for f in frames:
            if (isinstance(f, http2_flow.Http2Header) and f.priority) or isinstance(f, http2_flow.Http2PriorityUpdate):
                priority_cnt += 1
                assert f.stream_id == 1
                assert f.from_client is True
                assert f.priority["weight"] == priority[2]
                assert f.priority["depends_on"] == priority[1]
                assert f.priority["exclusive"] == priority[0]

        if priority[0]:
            assert priority_cnt == 1
        else:
            assert priority_cnt == 0

        assert len(self.master.state.flows) == 2
        assert self.priority_data == expected_priority


class TestStreamResetFromServer(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            h2_conn.reset_stream(event.stream_id, 0x8)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    def test_request_with_priority(self):
        h2_conn = self.setup_connection()

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
        )

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamReset):
                    done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        frames = self.master.state.flows[0].messages

        # Wait until the goaway frame has been send
        cnt = 0
        while not isinstance(frames[-1], http2_flow.Http2Goaway):
            cnt += 1
            assert cnt <= 10000000

        assert isinstance(frames[-2], http2_flow.Http2RstStream)
        assert frames[-2].error_code == 8
        assert frames[-2].stream_id == 1
        assert frames[-2].from_client is False
        assert isinstance(frames[-1], http2_flow.Http2Goaway)
        assert frames[-1].stream_id == 0
        assert frames[-1].error_code == 0
        assert frames[-1].last_stream_id == 0

        assert len(self.master.state.flows) == 2
        assert self.master.state.flows[1].response is None


class TestBodySizeLimit(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        return True

    def test_body_size_limit(self):
        self.options.body_size_limit = "20"

        h2_conn = self.setup_connection()

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            body=b'very long body over 20 characters long',
        )

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamReset):
                    done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        assert len(self.master.state.flows) == 1


class TestPushPromise(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        TestPushPromise.push_header_2 = [
            (b':authority', bytes("127.0.0.1:{}".format(cls.port), 'utf-8')),
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':path', b'/pushed_stream_foo'),
            (b'foo', b'bar')
        ]

        TestPushPromise.push_header_4 = [
            (b':authority', bytes("127.0.0.1:{}".format(cls.port), 'utf-8')),
            (b':method', b'GET'),
            (b':scheme', b'https'),
            (b':path', b'/pushed_stream_bar'),
            (b'foo', b'bar')
        ]

        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            if event.stream_id != 1:
                # ignore requests initiated by push promises
                return True

            h2_conn.send_headers(1, [(':status', '200')])
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.push_stream(1, 2, TestPushPromise.push_header_2)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.push_stream(1, 4, TestPushPromise.push_header_4)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.send_headers(2, [(':status', '200')])
            h2_conn.send_headers(4, [(':status', '200')])
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.send_data(1, b'regular_stream')
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.end_stream(1)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.send_data(2, b'pushed_stream_foo')
            h2_conn.end_stream(2)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.send_data(4, b'pushed_stream_bar')
            h2_conn.end_stream(4)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

        return True

    def test_push_promise(self):
        h2_conn = self.setup_connection()

        self._send_request(self.client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
            ('foo', 'bar')
        ])

        done = False
        ended_streams = 0
        pushed_streams = 0
        responses = 0
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False
            except:
                break
            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    ended_streams += 1
                elif isinstance(event, h2.events.PushedStreamReceived):
                    pushed_streams += 1
                elif isinstance(event, h2.events.ResponseReceived):
                    responses += 1
                if isinstance(event, h2.events.ConnectionTerminated):
                    done = True

            if responses == 3 and ended_streams == 3 and pushed_streams == 2:
                done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        assert ended_streams == 3
        assert pushed_streams == 2

        frames = self.master.state.flows[0].messages
        is_first_header = True
        push_received = []
        data_received = []
        for f in frames:
            if isinstance(f, http2_flow.Http2Header):
                if is_first_header:
                    is_first_header = False
                    assert f.headers == [
                        (b':authority', bytes("127.0.0.1:{}".format(self.server.server.address[1]), 'utf-8')),
                        (b':method', b'GET'),
                        (b':scheme', b'https'),
                        (b':path', b'/'),
                        (b'foo', b'bar')
                    ]
                else:
                    assert f.headers == [(b':status', b'200')]
            if isinstance(f, http2_flow.Http2Push):
                assert f.stream_id == 1
                assert f.from_client is False
                push_received.append(f.pushed_stream_id)
                if f.pushed_stream_id == 2:
                    assert f.headers == TestPushPromise.push_header_2
                elif f.pushed_stream_id == 4:
                    assert f.headers == TestPushPromise.push_header_4
                else:
                    assert False
            if isinstance(f, http2_flow.Http2Data):
                if f.stream_id not in data_received:
                    data_received.append(f.stream_id)
                    if f.stream_id == 1:
                        assert f.data == b'regular_stream'
                        assert f.length == len(b'regular_stream')
                    elif f.stream_id == 2:
                        assert f.data == b'pushed_stream_foo'
                        assert f.length == len(b'pushed_stream_foo')
                    elif f.stream_id == 4:
                        assert f.data == b'pushed_stream_bar'
                        assert f.length == len(b'pushed_stream_bar')
                    else:
                        assert False
                else:
                    assert f.data == b''
                    assert f.length == 0
                    assert f.end_stream is True
        assert not is_first_header
        assert push_received == [2, 4]
        assert data_received == [1, 2, 4]

        # Wait until the goaway frame has been send
        cnt = 0
        while not isinstance(frames[-1], http2_flow.Http2Goaway):
            cnt += 1
            assert cnt <= 10000000

        bodies = [flow.response.content for flow in self.master.state.flows if isinstance(flow, http.HTTPFlow)]
        assert len(bodies) == 3
        assert b'regular_stream' in bodies
        assert b'pushed_stream_foo' in bodies
        assert b'pushed_stream_bar' in bodies

        pushed_flows = [flow for flow in self.master.state.flows if isinstance(flow, http.HTTPFlow) and 'h2-pushed-stream' in flow.metadata]
        assert len(pushed_flows) == 2

    def test_push_promise_reset(self):
        h2_conn = self.setup_connection()

        self._send_request(self.client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
            ('foo', 'bar')
        ])

        done = False
        ended_streams = 0
        pushed_streams = 0
        responses = 0
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False

            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded) and event.stream_id == 1:
                    ended_streams += 1
                elif isinstance(event, h2.events.PushedStreamReceived):
                    pushed_streams += 1
                    h2_conn.reset_stream(event.pushed_stream_id, error_code=0x8)
                    self.client.wfile.write(h2_conn.data_to_send())
                    self.client.wfile.flush()
                elif isinstance(event, h2.events.ResponseReceived):
                    responses += 1
                if isinstance(event, h2.events.ConnectionTerminated):
                    done = True

            if responses >= 1 and ended_streams >= 1 and pushed_streams == 2:
                done = True

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        frames = self.master.state.flows[0].messages
        is_first_header = True
        push_received = []
        reset_received = []
        data_received = []
        for f in frames:
            if isinstance(f, http2_flow.Http2Header):
                if is_first_header:
                    is_first_header = False
                    assert f.headers == [
                        (b':authority', bytes("127.0.0.1:{}".format(self.server.server.address[1]), 'utf-8')),
                        (b':method', b'GET'),
                        (b':scheme', b'https'),
                        (b':path', b'/'),
                        (b'foo', b'bar')
                    ]
                else:
                    assert f.headers == [(b':status', b'200')]
            if isinstance(f, http2_flow.Http2Push):
                push_received.append(f.pushed_stream_id)
                if f.pushed_stream_id == 2:
                    assert f.headers == TestPushPromise.push_header_2
                elif f.pushed_stream_id == 4:
                    assert f.headers == TestPushPromise.push_header_4
                else:
                    assert False
            if isinstance(f, http2_flow.Http2RstStream):
                reset_received.append(f.stream_id)
            if isinstance(f, http2_flow.Http2Data):
                if f.stream_id not in data_received:
                    data_received.append(f.stream_id)
                    if f.stream_id == 1:
                        assert f.data == b'regular_stream'
                        assert f.length == len(b'regular_stream')
                    elif f.stream_id == 2:
                        assert f.data == b'pushed_stream_foo'
                        assert f.length == len(b'pushed_stream_foo')
                    elif f.stream_id == 4:
                        assert f.data == b'pushed_stream_bar'
                        assert f.length == len(b'pushed_stream_bar')
                    else:
                        assert False
                else:
                    assert f.data == b''
                    assert f.length == 0
                    assert f.end_stream is True

        assert push_received == [2, 4]
        assert reset_received == [2, 4]
        assert data_received == [1, 2, 4]

        bodies = [flow.response.content for flow in self.master.state.flows if isinstance(flow, http.HTTPFlow) and flow.response]
        assert len(bodies) >= 1
        assert b'regular_stream' in bodies
        # the other two bodies might not be transmitted before the reset


class TestConnectionLost(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.RequestReceived):
            h2_conn.send_headers(1, [(':status', '200')])
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
            return False

    def test_connection_lost(self):
        h2_conn = self.setup_connection()

        self._send_request(self.client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
            ('foo', 'bar')
        ])

        done = False
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                h2_conn.receive_data(raw)
            except exceptions.HttpException:
                print(traceback.format_exc())
                assert False
            except:
                break
            try:
                self.client.wfile.write(h2_conn.data_to_send())
                self.client.wfile.flush()
            except:
                break

        if len(self.master.state.flows) == 2:
            assert self.master.state.flows[1].response is None


class TestMaxConcurrentStreams(_Http2Test):

    @classmethod
    def setup_class(cls):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class(h2_server_settings={h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 2})

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            h2_conn.send_headers(event.stream_id, [
                (':status', '200'),
                ('X-Stream-ID', str(event.stream_id)),
            ])
            h2_conn.send_data(event.stream_id, 'Stream-ID {}'.format(event.stream_id).encode())
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    def test_max_concurrent_streams(self):
        h2_conn = self.setup_connection()
        new_streams = [1, 3, 5, 7, 9, 11]
        for stream_id in new_streams:
            # this will exceed MAX_CONCURRENT_STREAMS on the server connection
            # and cause mitmproxy to throttle stream creation to the server
            self._send_request(self.client.wfile, h2_conn, stream_id=stream_id, headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
                ('X-Stream-ID', str(stream_id)),
            ])

        ended_streams = 0
        while ended_streams != len(new_streams):
            try:
                header, body = http2.read_raw_frame(self.client.rfile)
                events = h2_conn.receive_data(b''.join([header, body]))
            except:
                break
            self.client.wfile.write(h2_conn.data_to_send())
            self.client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    ended_streams += 1

        h2_conn.close_connection()
        self.client.wfile.write(h2_conn.data_to_send())
        self.client.wfile.flush()

        frames = self.master.state.flows[0].messages
        header_received = dict(client=[], server=[])
        data_received = dict(client=[], server=[])
        settings_state = {}
        max_current_stream_key = int(h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS)
        for f in frames:
            if isinstance(f, http2_flow.Http2Settings):
                if max_current_stream_key in f.settings and f.settings[max_current_stream_key]['new_value'] == 2:
                    if f.from_client:
                        settings_state['client'] = True
                        assert f.ack is True
                    else:
                        settings_state['server'] = True
                        assert f.ack is False
            if isinstance(f, http2_flow.Http2Header):
                header_received['client' if f.from_client else 'server'].append(f.stream_id)
            if isinstance(f, http2_flow.Http2Data):
                data_received['client' if f.from_client else 'server'].append(f.stream_id)

        assert settings_state == {"client": True, "server": True}
        assert header_received == {'client': [1, 3, 5, 7, 9, 11],
                                   'server': [1, 3, 5, 7, 9, 11]}
        assert data_received == {'client': [],
                                 'server': [1, 1, 3, 3, 5, 5, 7, 7, 9, 9, 11, 11]}

        assert len(self.master.state.flows) == len(new_streams) + 1  # For http2 flow
        for flow in self.master.state.flows:
            if isinstance(flow, http.HTTPFlow):
                assert flow.response.status_code == 200
                assert b"Stream-ID " in flow.response.content


class TestConnectionTerminated(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.RequestReceived):
            h2_conn.close_connection(error_code=5, last_stream_id=42, additional_data=b'foobar')
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    def test_connection_terminated(self):
        h2_conn = self.setup_connection()

        self._send_request(self.client.wfile, h2_conn, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ])

        done = False
        connection_terminated_event = None
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)
                for event in events:
                    if isinstance(event, h2.events.ConnectionTerminated):
                        connection_terminated_event = event
                        done = True
            except:
                break

        frames = self.master.state.flows[0].messages
        assert isinstance(frames[-1], http2_flow.Http2Goaway)
        assert frames[-1].from_client is False
        assert frames[-1].stream_id == 0
        assert frames[-1].error_code == 5
        assert frames[-1].additional_data == b'foobar'
        assert frames[-1].last_stream_id == 42

        assert len(self.master.state.flows) == 2
        assert connection_terminated_event is not None
        assert connection_terminated_event.error_code == 5
        assert connection_terminated_event.last_stream_id == 42
        assert connection_terminated_event.additional_data == b'foobar'


class TestRequestStreaming(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.DataReceived):
            data = event.data
            assert data
            h2_conn.close_connection(error_code=5, last_stream_id=42, additional_data=data)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

        return True

    @pytest.mark.parametrize('streaming', [True, False])
    def test_request_streaming(self, streaming):
        class Stream:
            def requestheaders(self, f):
                f.request.stream = streaming

        self.master.addons.add(Stream())
        h2_conn = self.setup_connection()
        body = generators.RandomGenerator("bytes", 100)[:]
        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),

            ],
            body=body,
            streaming=True
        )
        done = False
        connection_terminated_event = None
        self.client.rfile.o.settimeout(2)
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)

                for event in events:
                    if isinstance(event, h2.events.ConnectionTerminated):
                        connection_terminated_event = event
                        done = True
            except:
                break

        frames = self.master.state.flows[0].messages
        for f in frames:
            if isinstance(f, http2_flow.Http2Data):
                data = f.data
                assert f.length == len(f.data)

        if streaming:
            assert isinstance(frames[-1], http2_flow.Http2Goaway)
            assert frames[-1].error_code == 5
            assert frames[-1].additional_data == data
            assert frames[-1].last_stream_id == 42
        else:
            assert not isinstance(frames[-1], http2_flow.Http2Goaway)

        if streaming:
            assert connection_terminated_event.additional_data == body
        else:
            assert connection_terminated_event is None


class TestResponseStreaming(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            TestResponseStreaming.data = generators.RandomGenerator("bytes", 100)[:]
            h2_conn.send_headers(event.stream_id, [
                (':status', '200'),
                ('content-length', '100')
            ])
            h2_conn.send_data(event.stream_id, TestResponseStreaming.data)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    @pytest.mark.parametrize('streaming', [True, False])
    def test_response_streaming(self, streaming):
        class Stream:
            def responseheaders(self, f):
                f.response.stream = streaming

        self.master.addons.add(Stream())
        h2_conn = self.setup_connection()
        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),

            ]
        )
        done = False
        self.client.rfile.o.settimeout(2)
        data = None
        while not done:
            try:
                raw = b''.join(http2.read_raw_frame(self.client.rfile))
                events = h2_conn.receive_data(raw)

                for event in events:
                    if isinstance(event, h2.events.DataReceived):
                        data = event.data
                        done = True
            except:
                break

        frames = self.master.state.flows[0].messages
        header_cnt = 0
        for f in frames:
            if isinstance(f, http2_flow.Http2Header):
                if header_cnt == 0:
                    header_cnt += 1
                    assert f.headers == [
                        (b':authority', bytes("127.0.0.1:{}".format(self.server.server.address[1]), 'utf-8')),
                        (b':method', b'GET'),
                        (b':scheme', b'https'),
                        (b':path', b'/'),
                    ]
                else:
                    header_cnt += 1
                    assert f.headers == [(b':status', b'200'), (b'content-length', b'100')]

        assert header_cnt == 2
        assert frames[-1].data == TestResponseStreaming.data
        assert frames[-1].length == len(TestResponseStreaming.data)

        if streaming:
            assert data
        else:
            assert data is None
