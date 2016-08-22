# coding=utf-8

from __future__ import (absolute_import, print_function, division)

import pytest
import os
import tempfile
import traceback

import h2

from mitmproxy import options
from mitmproxy.proxy.config import ProxyConfig

import netlib
from ..netlib import tservers as netlib_tservers
from netlib.exceptions import HttpException
from netlib.http.http2 import framereader

from . import tservers

import logging
logging.getLogger("hyper.packages.hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)
logging.getLogger("passlib.registry").setLevel(logging.WARNING)
logging.getLogger("PIL.Image").setLevel(logging.WARNING)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


requires_alpn = pytest.mark.skipif(
    not netlib.tcp.HAS_ALPN,
    reason='requires OpenSSL with ALPN support')


class _Http2ServerBase(netlib_tservers.ServerTestBase):
    ssl = dict(alpn_select=b'h2')

    class handler(netlib.tcp.BaseHandler):

        def handle(self):
            h2_conn = h2.connection.H2Connection(client_side=False, header_encoding=False)

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
                    raw = b''.join(framereader.http2_read_raw_frame(self.rfile))
                    events = h2_conn.receive_data(raw)
                except HttpException:
                    print(traceback.format_exc())
                    assert False
                except netlib.exceptions.TcpDisconnect:
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
                    except netlib.exceptions.TcpDisconnect:
                        done = True
                    except:
                        done = True
                        print(traceback.format_exc())
                        break

    def handle_server_event(self, event, h2_conn, rfile, wfile):
        raise NotImplementedError()


class _Http2TestBase(object):

    @classmethod
    def setup_class(cls):
        opts = cls.get_options()
        cls.config = ProxyConfig(opts)

        tmaster = tservers.TestMaster(opts, cls.config)
        tmaster.start_app(options.APP_HOST, options.APP_PORT)
        cls.proxy = tservers.ProxyThread(tmaster)
        cls.proxy.start()

    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()

    @classmethod
    def get_options(cls):
        opts = options.Options(
            listen_port=0,
            no_upstream_cert=False,
            ssl_insecure=True
        )
        opts.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return opts

    @property
    def master(self):
        return self.proxy.tmaster

    def setup(self):
        self.master.clear_log()
        self.master.state.clear()
        self.server.server.handle_server_event = self.handle_server_event

    def _setup_connection(self):
        client = netlib.tcp.TCPClient(("127.0.0.1", self.proxy.port))
        client.connect()

        # send CONNECT request
        client.wfile.write(
            b"CONNECT localhost:%d HTTP/1.1\r\n"
            b"Host: localhost:%d\r\n"
            b"\r\n" % (self.server.server.address.port, self.server.server.address.port)
        )
        client.wfile.flush()

        # read CONNECT response
        while client.rfile.readline() != b"\r\n":
            pass

        client.convert_to_ssl(alpn_protos=[b'h2'])

        h2_conn = h2.connection.H2Connection(client_side=True, header_encoding=False)
        h2_conn.initiate_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        return client, h2_conn

    def _send_request(self,
                      wfile,
                      h2_conn,
                      stream_id=1,
                      headers=None,
                      body=b'',
                      end_stream=None,
                      priority_exclusive=None,
                      priority_depends_on=None,
                      priority_weight=None):
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
            assert (b'client-foo', b'client-bar-1') in event.headers
            assert (b'client-foo', b'client-bar-2') in event.headers
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
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
                ('ClIeNt-FoO', 'client-bar-1'),
                ('ClIeNt-FoO', 'client-bar-2'),
            ],
            body=b'request body')

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.DataReceived):
                    response_body_buffer += event.data
                elif isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response.status_code == 200
        assert self.master.state.flows[0].response.headers['server-foo'] == 'server-bar'
        assert self.master.state.flows[0].response.headers['föo'] == 'bär'
        assert self.master.state.flows[0].response.body == b'response body'
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
                    headers.append(('priority_exclusive', event.priority_updated.exclusive))
                    headers.append(('priority_depends_on', event.priority_updated.depends_on))
                    headers.append(('priority_weight', event.priority_updated.weight))
                h2_conn.send_headers(event.stream_id, headers)
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    def test_request_with_priority(self):
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            priority_exclusive=True,
            priority_depends_on=42424242,
            priority_weight=42,
        )

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response.headers['priority_exclusive'] == 'True'
        assert self.master.state.flows[0].response.headers['priority_depends_on'] == '42424242'
        assert self.master.state.flows[0].response.headers['priority_weight'] == '42'

    def test_request_without_priority(self):
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
        )

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert 'priority_exclusive' not in self.master.state.flows[0].response.headers
        assert 'priority_depends_on' not in self.master.state.flows[0].response.headers
        assert 'priority_weight' not in self.master.state.flows[0].response.headers


@requires_alpn
class TestPriority(_Http2Test):
    priority_data = None

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.PriorityUpdated):
            cls.priority_data = (event.exclusive, event.depends_on, event.weight)
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

    def test_priority(self):
        client, h2_conn = self._setup_connection()

        h2_conn.prioritize(1, exclusive=True, depends_on=0, weight=42)
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
        )

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert self.priority_data == (True, 0, 42)


@requires_alpn
class TestPriorityWithExistingStream(_Http2Test):
    priority_data = []

    @classmethod
    def handle_server_event(cls, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.PriorityUpdated):
            cls.priority_data.append((event.exclusive, event.depends_on, event.weight))
        elif isinstance(event, h2.events.RequestReceived):
            assert not event.priority_updated

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
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        elif isinstance(event, h2.events.StreamEnded):
            h2_conn.end_stream(event.stream_id)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
        return True

    def test_priority_with_existing_stream(self):
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            end_stream=False,
        )

        h2_conn.prioritize(1, exclusive=True, depends_on=0, weight=42)
        h2_conn.end_stream(1)
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert self.priority_data == [(True, 0, 42)]


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
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
        )

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamReset):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

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
        self.config.options.body_size_limit = 20

        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            body=b'very long body over 20 characters long',
        )

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamReset):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

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
            h2_conn.push_stream(1, 2, [
                (':authority', "127.0.0.1:{}".format(cls.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/pushed_stream_foo'),
                ('foo', 'bar')
            ])
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
            h2_conn.send_data(2, b'pushed_stream_foo')
            h2_conn.send_data(4, b'pushed_stream_bar')
            wfile.write(h2_conn.data_to_send())
            wfile.flush()
            h2_conn.end_stream(1)
            h2_conn.end_stream(2)
            h2_conn.end_stream(4)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

        return True

    def test_push_promise(self):
        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
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
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False
            except:
                break
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

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
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert ended_streams == 3
        assert pushed_streams == 2

        bodies = [flow.response.body for flow in self.master.state.flows]
        assert len(bodies) == 3
        assert b'regular_stream' in bodies
        assert b'pushed_stream_foo' in bodies
        assert b'pushed_stream_bar' in bodies

    def test_push_promise_reset(self):
        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
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
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False

            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded) and event.stream_id == 1:
                    ended_streams += 1
                elif isinstance(event, h2.events.PushedStreamReceived):
                    pushed_streams += 1
                    h2_conn.reset_stream(event.pushed_stream_id, error_code=0x8)
                    client.wfile.write(h2_conn.data_to_send())
                    client.wfile.flush()
                elif isinstance(event, h2.events.ResponseReceived):
                    responses += 1
                if isinstance(event, h2.events.ConnectionTerminated):
                    done = True

            if responses >= 1 and ended_streams >= 1 and pushed_streams == 2:
                done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        bodies = [flow.response.body for flow in self.master.state.flows if flow.response]
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
        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, stream_id=1, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
            ('foo', 'bar')
        ])

        done = False
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
                h2_conn.receive_data(raw)
            except HttpException:
                print(traceback.format_exc())
                assert False
            except:
                break
            try:
                client.wfile.write(h2_conn.data_to_send())
                client.wfile.flush()
            except:
                break

        if len(self.master.state.flows) == 1:
            assert self.master.state.flows[0].response is None


@requires_alpn
class TestMaxConcurrentStreams(_Http2Test):

    @classmethod
    def setup_class(cls):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class(h2_server_settings={h2.settings.MAX_CONCURRENT_STREAMS: 2})

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
        client, h2_conn = self._setup_connection()
        new_streams = [1, 3, 5, 7, 9, 11]
        for stream_id in new_streams:
            # this will exceed MAX_CONCURRENT_STREAMS on the server connection
            # and cause mitmproxy to throttle stream creation to the server
            self._send_request(client.wfile, h2_conn, stream_id=stream_id, headers=[
                (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
                ('X-Stream-ID', str(stream_id)),
            ])

        ended_streams = 0
        while ended_streams != len(new_streams):
            try:
                header, body = framereader.http2_read_raw_frame(client.rfile)
                events = h2_conn.receive_data(b''.join([header, body]))
            except:
                break
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    ended_streams += 1

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == len(new_streams)
        for flow in self.master.state.flows:
            assert flow.response.status_code == 200
            assert b"Stream-ID " in flow.response.body


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
        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, headers=[
            (':authority', "127.0.0.1:{}".format(self.server.server.address.port)),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ])

        done = False
        connection_terminated_event = None
        while not done:
            try:
                raw = b''.join(framereader.http2_read_raw_frame(client.rfile))
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
