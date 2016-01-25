from __future__ import (absolute_import, print_function, division)

import inspect
import socket
import OpenSSL
import pytest
from io import BytesIO

import logging
logging.getLogger("hyper.packages.hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("passlib.utils.compat").setLevel(logging.WARNING)
logging.getLogger("passlib.registry").setLevel(logging.WARNING)
logging.getLogger("PIL.Image").setLevel(logging.WARNING)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)

import netlib
from netlib import tservers as netlib_tservers

import h2

from libmproxy import utils
from . import tservers

requires_alpn = pytest.mark.skipif(
    not OpenSSL._util.lib.Cryptography_HAS_ALPN,
    reason="requires OpenSSL with ALPN support")


class SimpleHttp2Server(netlib_tservers.ServerTestBase):
    ssl = dict(alpn_select=b'h2')

    class handler(netlib.tcp.BaseHandler):
        def handle(self):
            h2_conn = h2.connection.H2Connection(client_side=False)

            preamble = self.rfile.read(24)
            h2_conn.initiate_connection()
            h2_conn.receive_data(preamble)
            self.wfile.write(h2_conn.data_to_send())
            self.wfile.flush()

            while True:
                events = h2_conn.receive_data(utils.http2_read_frame(self.rfile))
                self.wfile.write(h2_conn.data_to_send())
                self.wfile.flush()

                for event in events:
                    if isinstance(event, h2.events.RequestReceived):
                        h2_conn.send_headers(1, [
                            (':status', '200'),
                            ('foo', 'bar'),
                        ])
                        h2_conn.send_data(1, b'foobar')
                        h2_conn.end_stream(1)
                        self.wfile.write(h2_conn.data_to_send())
                        self.wfile.flush()
                    elif isinstance(event, h2.events.ConnectionTerminated):
                        return


class PushHttp2Server(netlib_tservers.ServerTestBase):
    ssl = dict(alpn_select=b'h2')

    class handler(netlib.tcp.BaseHandler):
        def handle(self):
            h2_conn = h2.connection.H2Connection(client_side=False)

            preamble = self.rfile.read(24)
            h2_conn.initiate_connection()
            h2_conn.receive_data(preamble)
            self.wfile.write(h2_conn.data_to_send())
            self.wfile.flush()

            while True:
                events = h2_conn.receive_data(utils.http2_read_frame(self.rfile))
                self.wfile.write(h2_conn.data_to_send())
                self.wfile.flush()

                for event in events:
                    if isinstance(event, h2.events.RequestReceived):
                        h2_conn.send_headers(1, [(':status', '200')])
                        h2_conn.push_stream(1, 2, [
                            (':authority', "127.0.0.1:%s" % self.address.port),
                            (':method', 'GET'),
                            (':scheme', 'https'),
                            (':path', '/pushed_stream_foo'),
                            ('foo', 'bar')
                        ])
                        h2_conn.push_stream(1, 4, [
                            (':authority', "127.0.0.1:%s" % self.address.port),
                            (':method', 'GET'),
                            (':scheme', 'https'),
                            (':path', '/pushed_stream_bar'),
                            ('foo', 'bar')
                        ])
                        self.wfile.write(h2_conn.data_to_send())
                        self.wfile.flush()

                        h2_conn.send_headers(2, [(':status', '202')])
                        h2_conn.send_headers(4, [(':status', '204')])
                        h2_conn.send_data(1, b'regular_stream')
                        h2_conn.send_data(2, b'pushed_stream_foo')
                        h2_conn.send_data(4, b'pushed_stream_bar')
                        h2_conn.end_stream(1)
                        h2_conn.end_stream(2)
                        h2_conn.end_stream(4)
                        self.wfile.write(h2_conn.data_to_send())
                        self.wfile.flush()
                        print("HERE")
                    elif isinstance(event, h2.events.ConnectionTerminated):
                        return


@requires_alpn
class TestHttp2(tservers.ProxTestBase):
    def _setup_connection(self):
        self.config.http2 = True

        client = netlib.tcp.TCPClient(("127.0.0.1", self.proxy.port))
        client.connect()

        # send CONNECT request
        client.wfile.write(
            b"CONNECT localhost:%d HTTP/1.1\r\n"
            b"Host: localhost:%d\r\n"
            b"\r\n" % (self.server.port, self.server.port)
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

    def _send_request(self, wfile, h2_conn, stream_id=1, headers=[], end_stream=True):
        h2_conn.send_headers(
            stream_id=stream_id,
            headers=headers,
            end_stream=end_stream,
        )
        wfile.write(h2_conn.data_to_send())
        wfile.flush()

    def test_simple(self):
        self.server = SimpleHttp2Server()
        self.server.setup_class()

        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, headers=[
            (':authority', "127.0.0.1:%s" % self.server.port),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ])

        done = False
        while not done:
            events = h2_conn.receive_data(utils.http2_read_frame(client.rfile))
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    done = True

        h2_conn.close_connection()
        client.wfile.write(h2_conn.data_to_send())
        client.wfile.flush()

        self.server.teardown_class()

        assert len(self.master.state.flows) == 1
        assert self.master.state.flows[0].response.status_code == 200
        assert self.master.state.flows[0].response.headers['foo'] == 'bar'
        assert self.master.state.flows[0].response.body == b'foobar'

    def test_pushed_streams(self):
        self.server = PushHttp2Server()
        self.server.setup_class()

        client, h2_conn = self._setup_connection()

        self._send_request(client.wfile, h2_conn, headers=[
            (':authority', "127.0.0.1:%s" % self.server.port),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
            ('foo', 'bar')
        ])

        ended_streams = 0
        while ended_streams != 3:
            try:
                events = h2_conn.receive_data(utils.http2_read_frame(client.rfile))
            except:
                break
            client.wfile.write(h2_conn.data_to_send())
            client.wfile.flush()

            for event in events:
                if isinstance(event, h2.events.StreamEnded):
                    ended_streams += 1

        self.server.teardown_class()

        assert len(self.master.state.flows) == 3
        assert self.master.state.flows[0].response.body == b'regular_stream'
        assert self.master.state.flows[1].response.body == b'pushed_stream_foo'
        assert self.master.state.flows[2].response.body == b'pushed_stream_bar'
