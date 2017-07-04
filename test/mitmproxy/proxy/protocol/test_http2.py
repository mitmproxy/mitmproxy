# coding=utf-8


import os
import tempfile
import traceback
import pytest
import h2

from mitmproxy import options
from mitmproxy.proxy.config import ProxyConfig

import mitmproxy.net
from ...net import tservers as net_tservers
from mitmproxy import exceptions
from mitmproxy.net.http import http1, http2
from pathod.language import generators

from ... import tservers
from ....conftest import requires_alpn

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
        opts = cls.get_options()
        cls.config = ProxyConfig(opts)

        tmaster = tservers.TestMaster(opts, cls.config)
        cls.proxy = tservers.ProxyThread(tmaster)
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
        opts.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
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

        self.client.convert_to_ssl(alpn_protos=[b'h2'])

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


@requires_alpn
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

        self._send_request(
            self.client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address[1])),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
                ('self.client-FoO', 'self.client-bar-1'),
                ('self.client-FoO', 'self.client-bar-2'),
            ],
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

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response.status_code == 200
        assert self.master.state.flows[0].response.headers['server-foo'] == 'server-bar'
        assert self.master.state.flows[0].response.headers['föo'] == 'bär'
        assert self.master.state.flows[0].response.content == b'response body'
        assert self.request_body_buffer == b'request body'
        assert response_body_buffer == b'response body'


@requires_alpn
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
        self.config.options.http2_priority = http2_priority_enabled

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

        assert len(self.master.state.flows) == 1

        resp = self.master.state.flows[0].response
        assert resp.headers.get('priority_exclusive', None) == expected_priority[0]
        assert resp.headers.get('priority_depends_on', None) == expected_priority[1]
        assert resp.headers.get('priority_weight', None) == expected_priority[2]


@requires_alpn
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
        self.config.options.http2_priority = http2_priority_enabled
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

        assert len(self.master.state.flows) == 1
        assert self.priority_data == expected_priority


@requires_alpn
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

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response is None


@requires_alpn
class TestBodySizeLimit(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        return True

    def test_body_size_limit(self):
        self.config.options.body_size_limit = "20"
        self.config.options._processed["body_size_limit"] = 20

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

        assert len(self.master.state.flows) == 0


@requires_alpn
class TestPushPromise(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            if event.stream_id != 1:
                # ignore requests initiated by push promises
                return True

            h2_conn.send_headers(1, [(':status', '200')])
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.push_stream(1, 2, [
                (':authority', "127.0.0.1:{}".format(cls.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/pushed_stream_foo'),
                ('foo', 'bar')
            ])
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

            h2_conn.push_stream(1, 4, [
                (':authority', "127.0.0.1:{}".format(cls.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/pushed_stream_bar'),
                ('foo', 'bar')
            ])
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

        bodies = [flow.response.content for flow in self.master.state.flows]
        assert len(bodies) == 3
        assert b'regular_stream' in bodies
        assert b'pushed_stream_foo' in bodies
        assert b'pushed_stream_bar' in bodies

        pushed_flows = [flow for flow in self.master.state.flows if 'h2-pushed-stream' in flow.metadata]
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

        bodies = [flow.response.content for flow in self.master.state.flows if flow.response]
        assert len(bodies) >= 1
        assert b'regular_stream' in bodies
        # the other two bodies might not be transmitted before the reset


@requires_alpn
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

        if len(self.master.state.flows) == 1:
            assert self.master.state.flows[0].response is None


@requires_alpn
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

        assert len(self.master.state.flows) == len(new_streams)
        for flow in self.master.state.flows:
            assert flow.response.status_code == 200
            assert b"Stream-ID " in flow.response.content


@requires_alpn
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

        assert len(self.master.state.flows) == 1
        assert connection_terminated_event is not None
        assert connection_terminated_event.error_code == 5
        assert connection_terminated_event.last_stream_id == 42
        assert connection_terminated_event.additional_data == b'foobar'


@requires_alpn
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

        if streaming:
            assert connection_terminated_event.additional_data == body
        else:
            assert connection_terminated_event is None


@requires_alpn
class TestResponseStreaming(_Http2Test):

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            data = generators.RandomGenerator("bytes", 100)[:]
            h2_conn.send_headers(event.stream_id, [
                (':status', '200'),
                ('content-length', '100')
            ])
            h2_conn.send_data(event.stream_id, data)
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

        if streaming:
            assert data
        else:
            assert data is None
