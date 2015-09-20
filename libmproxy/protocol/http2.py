from __future__ import (absolute_import, print_function, division)
from Queue import Queue
import socket
import threading

import backports.socketpair
import time

from hyperframe.frame import (
    HeadersFrame,
    DataFrame,
    SettingsFrame,
    WindowUpdateFrame,
    PriorityFrame,
    AltSvcFrame,
    BlockedFrame,
)

from netlib.http import http1, http2
from netlib.http.http2 import Http2ClientConnection, Http2ServerConnection, make_response
from netlib.tcp import Reader, ssl_read_select
from ..exceptions import Http2ProtocolException, ProtocolException
from ..models import HTTPRequest, HTTPResponse
from .base import Layer
from .http import _StreamingHttpLayer, HttpLayer

assert backports.socketpair


class Http2Layer(Layer):

    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        if mode != "transparent":
            raise NotImplementedError("HTTP2 supports transparent mode only")

        self.client_conn = Http2ClientConnection(self.client_conn)
        self.server_conn = Http2ServerConnection(self.server_conn)

        # make sure that we only pass actual SSL.Connection objects in here,
        # because otherwise ssl_read_select fails!
        self.active_conns = []

        self.client_conn.preface()
        self.active_conns.append(self.client_conn.connection)
        if self.server_conn:
            self.server_conn.preface()
            self.active_conns.append(self.server_conn.connection)

    def connect(self):
        self.server_conn.connect()
        self.active_conns.append(self.server_conn.connection)

    def set_server(self):
        raise NotImplementedError("Cannot change server for HTTP2 connections.")

    def disconnect(self):
        raise NotImplementedError("Cannot dis- or reconnect in HTTP2 connections.")

    def __call__(self):
        client = self.client_conn
        server = self.server_conn

        try:
            while True:
                r = ssl_read_select(self.active_conns, 10)
                for conn in r:
                    source = client if conn == client.connection else server

                    frame = source.read_frame()
                    self.log("receive frame", "debug", (source.__class__.__name__, repr(frame)))

                    is_new_stream = (
                        isinstance(frame, HeadersFrame) and
                        source == client and
                        frame.stream_id not in source.streams
                    )
                    is_server_headers = (
                        isinstance(frame, HeadersFrame) and
                        source == server and
                        frame.stream_id in source.streams
                    )
                    is_data_frame = (
                        isinstance(frame, DataFrame) and
                        frame.stream_id in source.streams
                    )
                    is_settings_frame = (
                        isinstance(frame, SettingsFrame) and
                        frame.stream_id == 0
                    )
                    is_window_update_frame = (
                        isinstance(frame, WindowUpdateFrame)
                    )
                    is_ignored_frame = (
                        isinstance(frame, PriorityFrame) or
                        isinstance(frame, AltSvcFrame) or
                        isinstance(frame, BlockedFrame)
                    )
                    if is_new_stream:
                        self._create_new_stream(frame, source)
                    elif is_server_headers:
                        self._process_server_headers(frame, source)
                    elif is_data_frame:
                        self._process_data_frame(frame, source)
                    elif is_settings_frame:
                        self._process_settings_frame(frame, source)
                    elif is_window_update_frame:
                        self._process_window_update_frame(frame)
                    elif is_ignored_frame:
                        pass
                    else:
                        raise Http2ProtocolException("Unexpected Frame: %s" % repr(frame))

        finally:
            self.log("Waiting for streams to finish...", "debug")
            for stream in self.client_conn.streams.values() + self.server_conn.streams.values():
                stream.join()

    def _process_window_update_frame(self, window_update_frame):
        pass  # yolo flow control

    def _process_settings_frame(self, settings_frame, source):
        if 'ACK' in settings_frame.flags:
            pass
        else:
            # yolo settings processing
            settings_ack_frame = SettingsFrame(0)  # TODO: use new hyperframe init
            settings_ack_frame.flags = ['ACK']
            source.send_frame(settings_ack_frame)

    def _process_data_frame(self, data_frame, source):
        stream = source.streams[data_frame.stream_id]
        if source == self.client_conn:
            target = stream.into_client_conn
        else:
            target = stream.into_server_conn

        if len(data_frame.data) > 0:
            chunk = b"%x\r\n%s\r\n" % (len(data_frame.data), data_frame.data)
            target.sendall(chunk)

        if 'END_STREAM' in data_frame.flags:
            target.sendall("0\r\n\r\n")
            target.shutdown(socket.SHUT_WR)

    def _create_new_stream(self, headers_frame, source):
        header_frames, headers = self.client_conn.read_headers(headers_frame)
        stream = Stream(self, headers_frame.stream_id)
        source.streams[headers_frame.stream_id] = stream
        stream.start()

        stream.client_conn.headers.put(headers)
        if 'END_STREAM' in header_frames[-1].flags:
            stream.into_client_conn.sendall("0\r\n\r\n")
            stream.into_client_conn.shutdown(socket.SHUT_WR)

    def _process_server_headers(self, headers_frame, source):
        header_frames, headers = self.server_conn.read_headers(headers_frame)
        stream = source.streams[headers_frame.stream_id]

        stream.server_conn.headers.put(headers)
        if 'END_STREAM' in header_frames[-1].flags:
            stream.into_server_conn.sendall("0\r\n\r\n")
            stream.into_server_conn.shutdown(socket.SHUT_WR)


class StreamConnection(object):
    def __init__(self, stream_id, connection, original_connection):
        self.original_connection = original_connection
        self.rfile = Reader(connection.makefile('rb', -1))
        self.headers = Queue()
        self.stream_id = stream_id

    @property
    def address(self):
        return self.original_connection.address

    @property
    def tls_established(self):
        return self.original_connection.tls_established

    def __nonzero__(self):
        return bool(self.original_connection)


class Stream(_StreamingHttpLayer, threading.Thread):

    def __init__(self, ctx, client_stream_id):
        """
        :type ctx: Http2Layer
        """
        super(Stream, self).__init__(ctx)

        self.ctx = self.ctx

        a, b = socket.socketpair()
        self.client_conn = StreamConnection(client_stream_id, a, self.ctx.client_conn)
        self.server_conn = StreamConnection(None, b, self.ctx.server_conn)
        self.into_client_conn = b
        self.into_server_conn = a

    def read_request(self):
        timestamp_start = time.time()
        headers = self.client_conn.headers.get()
        body = b"".join(http1.read_body(self.client_conn.rfile, None, self.config.body_size_limit))
        timestamp_end = time.time()
        req = http2.make_request(headers, body, timestamp_start, timestamp_end)
        return HTTPRequest.wrap(req)

    def send_request(self, request):
        # (The end_stream handling is too simple for a CONNECT request)
        headers = http2.assemble_request_headers(request)

        # This is the first time we communicate with the server.
        # We now get the stream id and need to register ourselves.
        server_stream_id = self.ctx.server_conn.send_headers(
            headers,
            None,
            end_stream=not request.body
        )
        self.server_conn.stream_id = server_stream_id
        self.ctx.server_conn.streams[server_stream_id] = self
        if request.body:
            self.ctx.server_conn.send_data(request.body, self.server_conn.stream_id, end_stream=True)

    def read_response_headers(self):
        timestamp_start = time.time()
        headers = self.server_conn.headers.get()
        resp = make_response(headers, None, timestamp_start, None)
        return HTTPResponse.wrap(resp)

    def read_response_body(self, request, response):
        return http1.read_body(self.server_conn.rfile, None, self.config.body_size_limit)

    def send_response_headers(self, response):
        headers = http2.assemble_response_headers(response)
        self.ctx.client_conn.send_headers(headers, self.client_conn.stream_id, end_stream=False)

    def send_response_body(self, response, chunks):
        if chunks:
            for chunk in chunks:
                self.ctx.client_conn.send_data(chunk, self.client_conn.stream_id, end_stream=False)
        self.ctx.client_conn.send_data("", self.client_conn.stream_id, end_stream=True)

    def check_close_connection(self, flow):
        # RFC 7540 8.1: An HTTP request/response exchange fully consumes a single stream.
        return True

    def run(self):
        layer = HttpLayer(self, "transparent")
        try:
            layer()
        except ProtocolException as e:
            self.log(e, "info")
            # TODO: Send RST_STREAM?
