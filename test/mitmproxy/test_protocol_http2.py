from __future__ import (absolute_import, print_function, division)

import OpenSSL
import pytest
import traceback
import os
import tempfile

from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.cmdline import APP_HOST, APP_PORT

import logging
logging.getLogger("hyper.packages.hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)
logging.getLogger("passlib.registry").setLevel(logging.WARNING)
logging.getLogger("PIL.Image").setLevel(logging.WARNING)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)

import netlib
from ..netlib import tservers as netlib_tservers
from netlib.utils import http2_read_raw_frame

import h2

from . import tservers

requires_alpn = pytest.mark.skipif(
    not netlib.tcp.HAS_ALPN,
    reason="requires OpenSSL with ALPN support")


class _Http2ServerBase(netlib_tservers.ServerTestBase):
    ssl = dict(alpn_select=b'h2')

    class handler(netlib.tcp.BaseHandler):

        def handle(self):
            h2_conn = h2.connection.H2Connection(client_side=False)

            preamble = self.rfile.read(24)
            h2_conn.initiate_connection()
            h2_conn.receive_data(preamble)
            self.wfile.write(h2_conn.data_to_send())
            self.wfile.flush()

            done = False
            while not done:
                try:
                    raw = b''.join(http2_read_raw_frame(self.rfile))
                    events = h2_conn.receive_data(raw)
                except:
                    break
                self.wfile.write(h2_conn.data_to_send())
                self.wfile.flush()

                for event in events:
                    try:
                        if not self.server.handle_server_event(event, h2_conn, self.rfile, self.wfile):
                            done = True
                            break
                    except Exception as e:
                        print(repr(e))
                        print(traceback.format_exc())
                        done = True
                        break

    def handle_server_event(self, h2_conn, rfile, wfile):
        raise NotImplementedError()


class _Http2TestBase(object):

    @classmethod
    def setup_class(self):
        self.config = ProxyConfig(**self.get_proxy_config())

        tmaster = tservers.TestMaster(self.config)
        tmaster.start_app(APP_HOST, APP_PORT)
        self.proxy = tservers.ProxyThread(tmaster)
        self.proxy.start()

    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()

    @property
    def master(self):
        return self.proxy.tmaster

    @classmethod
    def get_proxy_config(cls):
        cls.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return dict(
            no_upstream_cert = False,
            cadir = cls.cadir,
            authenticator = None,
        )

    def setup(self):
        self.master.clear_log()
        self.master.state.clear()
        self.server.server.handle_server_event = self.handle_server_event

    def _setup_connection(self):
        self.config.http2 = True

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
        while client.rfile.readline() != "\r\n":
            pass

        client.convert_to_ssl(alpn_protos=[b'h2'])

        h2_conn = h2.connection.H2Connection(client_side=True)
        h2_conn.initiate_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        return client, h2_conn

    def _send_request(self, wfile, h2_conn, stream_id=1, headers=[], body=b''):
        h2_conn.send_headers(
            stream_id=stream_id,
            headers=headers,
            end_stream=(len(body) == 0),
        )
        if body:
            h2_conn.send_data(stream_id, body)
            h2_conn.end_stream(stream_id)
        wfile.write(h2_conn.data_to_send())
        wfile.flush()


@requires_alpn
class TestSimple(_Http2TestBase, _Http2ServerBase):

    @classmethod
    def setup_class(self):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class()

    @classmethod
    def teardown_class(self):
        _Http2TestBase.teardown_class()
        _Http2ServerBase.teardown_class()

    @classmethod
    def handle_server_event(self, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            h2_conn.send_headers(1, [
                (':status', '200'),
                ('foo', 'bar'),
            ])
            h2_conn.send_data(1, b'foobar')
            h2_conn.end_stream(1)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

        return True

    def test_simple(self):
        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, headers=[
            (':authority', "127.0.0.1:%s" % self.server.server.address.port),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ], body='my request body echoed back to me')

        done = False
        while not done:
            try:
                events = h2_conn.receive_data(b''.join(http2_read_raw_frame(client.rfile)))
            except:
                break
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response.status_code == 200
        assert self.master.state.flows[0].response.headers['foo'] == 'bar'
        assert self.master.state.flows[0].response.body == b'foobar'


@requires_alpn
class TestWithBodies(_Http2TestBase, _Http2ServerBase):
    tmp_data_buffer_foobar = b''

    @classmethod
    def setup_class(self):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class()

    @classmethod
    def teardown_class(self):
        _Http2TestBase.teardown_class()
        _Http2ServerBase.teardown_class()

    @classmethod
    def handle_server_event(self, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        if isinstance(event, h2.events.DataReceived):
            self.tmp_data_buffer_foobar += event.data
        elif isinstance(event, h2.events.StreamEnded):
            h2_conn.send_headers(1, [
                (':status', '200'),
            ])
            h2_conn.send_data(1, self.tmp_data_buffer_foobar)
            h2_conn.end_stream(1)
            wfile.write(h2_conn.data_to_send())
            wfile.flush()

        return True

    def test_with_bodies(self):
        client, h2_conn = self._setup_connection()

        self._send_request(
            client.wfile,
            h2_conn,
            headers=[
                (':authority', "127.0.0.1:%s" % self.server.server.address.port),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/'),
            ],
            body='foobar with request body',
        )

        done = False
        while not done:
            try:
                events = h2_conn.receive_data(b''.join(http2_read_raw_frame(client.rfile)))
            except:
                break
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        assert self.master.state.flows[0].response.body == b'foobar with request body'


@requires_alpn
class TestPushPromise(_Http2TestBase, _Http2ServerBase):

    @classmethod
    def setup_class(self):
        _Http2TestBase.setup_class()
        _Http2ServerBase.setup_class()

    @classmethod
    def teardown_class(self):
        _Http2TestBase.teardown_class()
        _Http2ServerBase.teardown_class()

    @classmethod
    def handle_server_event(self, event, h2_conn, rfile, wfile):
        if isinstance(event, h2.events.ConnectionTerminated):
            return False
        elif isinstance(event, h2.events.RequestReceived):
            if event.stream_id != 1:
                # ignore requests initiated by push promises
                return True

            h2_conn.send_headers(1, [(':status', '200')])
            h2_conn.push_stream(1, 2, [
                (':authority', "127.0.0.1:%s" % self.port),
                (':method', 'GET'),
                (':scheme', 'https'),
                (':path', '/pushed_stream_foo'),
                ('foo', 'bar')
            ])
            h2_conn.push_stream(1, 4, [
                (':authority', "127.0.0.1:%s" % self.port),
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
            (':authority', "127.0.0.1:%s" % self.server.server.address.port),
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
                raw = b''.join(http2_read_raw_frame(client.rfile))
                events = h2_conn.receive_data(raw)
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
            (':authority', "127.0.0.1:%s" % self.server.server.address.port),
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
                events = h2_conn.receive_data(b''.join(http2_read_raw_frame(client.rfile)))
            except:
                break
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
