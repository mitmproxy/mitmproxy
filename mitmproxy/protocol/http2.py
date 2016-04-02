from __future__ import (absolute_import, print_function, division)

import threading
import time
from six.moves import queue

import h2
import six
from h2.connection import H2Connection

from netlib.tcp import ssl_read_select
from netlib.exceptions import HttpException
from netlib.http import Headers
from netlib.utils import http2_read_raw_frame

from .base import Layer
from .http import _HttpTransmissionLayer, HttpLayer
from .. import utils
from ..models import HTTPRequest, HTTPResponse


class SafeH2Connection(H2Connection):

    def __init__(self, conn, *args, **kwargs):
        super(SafeH2Connection, self).__init__(*args, **kwargs)
        self.conn = conn
        self.lock = threading.RLock()

    def safe_close_connection(self, error_code):
        with self.lock:
            self.close_connection(error_code)
            self.conn.send(self.data_to_send())

    def safe_increment_flow_control(self, stream_id, length):
        if length == 0:
            return

        with self.lock:
            self.increment_flow_control_window(length)
            self.conn.send(self.data_to_send())
        with self.lock:
            if stream_id in self.streams and not self.streams[stream_id].closed:
                self.increment_flow_control_window(length, stream_id=stream_id)
                self.conn.send(self.data_to_send())

    def safe_reset_stream(self, stream_id, error_code):
        with self.lock:
            try:
                self.reset_stream(stream_id, error_code)
            except h2.exceptions.StreamClosedError:
                # stream is already closed - good
                pass
            self.conn.send(self.data_to_send())

    def safe_update_settings(self, new_settings):
        with self.lock:
            self.update_settings(new_settings)
            self.conn.send(self.data_to_send())

    def safe_send_headers(self, is_zombie, stream_id, headers):
        with self.lock:
            if is_zombie():
                return
            self.send_headers(stream_id, headers)
            self.conn.send(self.data_to_send())

    def safe_send_body(self, is_zombie, stream_id, chunks):
        for chunk in chunks:
            position = 0
            while position < len(chunk):
                self.lock.acquire()
                if is_zombie():
                    self.lock.release()
                    return
                max_outbound_frame_size = self.max_outbound_frame_size
                frame_chunk = chunk[position:position + max_outbound_frame_size]
                if self.local_flow_control_window(stream_id) < len(frame_chunk):
                    self.lock.release()
                    time.sleep(0)
                    continue
                self.send_data(stream_id, frame_chunk)
                self.conn.send(self.data_to_send())
                self.lock.release()
                position += max_outbound_frame_size
        with self.lock:
            if is_zombie():
                return
            self.end_stream(stream_id)
            self.conn.send(self.data_to_send())


class Http2Layer(Layer):

    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.streams = dict()
        self.client_reset_streams = []
        self.server_reset_streams = []
        self.server_to_client_stream_ids = dict([(0, 0)])
        self.client_conn.h2 = SafeH2Connection(self.client_conn, client_side=False)

        # make sure that we only pass actual SSL.Connection objects in here,
        # because otherwise ssl_read_select fails!
        self.active_conns = [self.client_conn.connection]

    def _initiate_server_conn(self):
        self.server_conn.h2 = SafeH2Connection(self.server_conn, client_side=True)
        self.server_conn.h2.initiate_connection()
        self.server_conn.send(self.server_conn.h2.data_to_send())
        self.active_conns.append(self.server_conn.connection)

    def connect(self):  # pragma: no cover
        raise ValueError("CONNECT inside an HTTP2 stream is not supported.")
        # self.ctx.connect()
        # self.server_conn.connect()
        # self._initiate_server_conn()

    def set_server(self):  # pragma: no cover
        raise NotImplementedError("Cannot change server for HTTP2 connections.")

    def disconnect(self):  # pragma: no cover
        raise NotImplementedError("Cannot dis- or reconnect in HTTP2 connections.")

    def next_layer(self):  # pragma: no cover
        # WebSockets over HTTP/2?
        # CONNECT for proxying?
        raise NotImplementedError()

    def _handle_event(self, event, source_conn, other_conn, is_server):
        self.log(
            "HTTP2 Event from {}".format("server" if is_server else "client"),
            "debug",
            [repr(event)]
        )

        if hasattr(event, 'stream_id'):
            if is_server and event.stream_id % 2 == 1:
                eid = self.server_to_client_stream_ids[event.stream_id]
            else:
                eid = event.stream_id

        if isinstance(event, h2.events.RequestReceived):
            headers = Headers([[str(k), str(v)] for k, v in event.headers])
            self.streams[eid] = Http2SingleStreamLayer(self, eid, headers)
            self.streams[eid].timestamp_start = time.time()
            self.streams[eid].start()
        elif isinstance(event, h2.events.ResponseReceived):
            headers = Headers([[str(k), str(v)] for k, v in event.headers])
            self.streams[eid].queued_data_length = 0
            self.streams[eid].timestamp_start = time.time()
            self.streams[eid].response_headers = headers
            self.streams[eid].response_arrived.set()
        elif isinstance(event, h2.events.DataReceived):
            if self.config.body_size_limit and self.streams[eid].queued_data_length > self.config.body_size_limit:
                raise HttpException("HTTP body too large. Limit is {}.".format(self.config.body_size_limit))
            self.streams[eid].data_queue.put(event.data)
            self.streams[eid].queued_data_length += len(event.data)
            source_conn.h2.safe_increment_flow_control(event.stream_id, event.flow_controlled_length)
        elif isinstance(event, h2.events.StreamEnded):
            self.streams[eid].timestamp_end = time.time()
            self.streams[eid].data_finished.set()
        elif isinstance(event, h2.events.StreamReset):
            self.streams[eid].zombie = time.time()
            self.client_reset_streams.append(self.streams[eid].client_stream_id)
            if self.streams[eid].server_stream_id:
                self.server_reset_streams.append(self.streams[eid].server_stream_id)
            if eid in self.streams and event.error_code == 0x8:
                if is_server:
                    other_stream_id = self.streams[eid].client_stream_id
                else:
                    other_stream_id = self.streams[eid].server_stream_id
                if other_stream_id is not None:
                    other_conn.h2.safe_reset_stream(other_stream_id, event.error_code)
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            new_settings = dict([(id, cs.new_value) for (id, cs) in six.iteritems(event.changed_settings)])
            other_conn.h2.safe_update_settings(new_settings)
        elif isinstance(event, h2.events.ConnectionTerminated):
            # Do not immediately terminate the other connection.
            # Some streams might be still sending data to the client.
            return False
        elif isinstance(event, h2.events.PushedStreamReceived):
            # pushed stream ids should be uniq and not dependent on race conditions
            # only the parent stream id must be looked up first
            parent_eid = self.server_to_client_stream_ids[event.parent_stream_id]
            with self.client_conn.h2.lock:
                self.client_conn.h2.push_stream(parent_eid, event.pushed_stream_id, event.headers)

            headers = Headers([[str(k), str(v)] for k, v in event.headers])
            headers['x-mitmproxy-pushed'] = 'true'
            self.streams[event.pushed_stream_id] = Http2SingleStreamLayer(self, event.pushed_stream_id, headers)
            self.streams[event.pushed_stream_id].timestamp_start = time.time()
            self.streams[event.pushed_stream_id].pushed = True
            self.streams[event.pushed_stream_id].parent_stream_id = parent_eid
            self.streams[event.pushed_stream_id].timestamp_end = time.time()
            self.streams[event.pushed_stream_id].request_data_finished.set()
            self.streams[event.pushed_stream_id].start()
        elif isinstance(event, h2.events.TrailersReceived):
            raise NotImplementedError()

        return True

    def _cleanup_streams(self):
        death_time = time.time() - 10
        for stream_id in self.streams.keys():
            zombie = self.streams[stream_id].zombie
            if zombie and zombie <= death_time:
                self.streams.pop(stream_id, None)

    def __call__(self):
        if self.server_conn:
            self._initiate_server_conn()

        preamble = self.client_conn.rfile.read(24)
        self.client_conn.h2.initiate_connection()
        self.client_conn.h2.receive_data(preamble)
        self.client_conn.send(self.client_conn.h2.data_to_send())

        while True:
            r = ssl_read_select(self.active_conns, 1)
            for conn in r:
                source_conn = self.client_conn if conn == self.client_conn.connection else self.server_conn
                other_conn = self.server_conn if conn == self.client_conn.connection else self.client_conn
                is_server = (conn == self.server_conn.connection)

                with source_conn.h2.lock:
                    try:
                        raw_frame = b''.join(http2_read_raw_frame(source_conn.rfile))
                    except:
                        for stream in self.streams.values():
                            stream.zombie = time.time()
                        return

                    events = source_conn.h2.receive_data(raw_frame)
                    source_conn.send(source_conn.h2.data_to_send())

                    for event in events:
                        if not self._handle_event(event, source_conn, other_conn, is_server):
                            return

            self._cleanup_streams()


class Http2SingleStreamLayer(_HttpTransmissionLayer, threading.Thread):

    def __init__(self, ctx, stream_id, request_headers):
        super(Http2SingleStreamLayer, self).__init__(ctx)
        self.zombie = None
        self.client_stream_id = stream_id
        self.server_stream_id = None
        self.request_headers = request_headers
        self.response_headers = None
        self.pushed = False

        self.request_data_queue = queue.Queue()
        self.request_queued_data_length = 0
        self.request_data_finished = threading.Event()

        self.response_arrived = threading.Event()
        self.response_data_queue = queue.Queue()
        self.response_queued_data_length = 0
        self.response_data_finished = threading.Event()

    @property
    def data_queue(self):
        if self.response_arrived.is_set():
            return self.response_data_queue
        else:
            return self.request_data_queue

    @property
    def queued_data_length(self):
        if self.response_arrived.is_set():
            return self.response_queued_data_length
        else:
            return self.request_queued_data_length

    @property
    def data_finished(self):
        if self.response_arrived.is_set():
            return self.response_data_finished
        else:
            return self.request_data_finished

    @queued_data_length.setter
    def queued_data_length(self, v):
        if self.response_arrived.is_set():
            return self.response_queued_data_length
        else:
            return self.request_queued_data_length

    def is_zombie(self):
        return self.zombie is not None

    def read_request(self):
        self.request_data_finished.wait()

        authority = self.request_headers.get(':authority', '')
        method = self.request_headers.get(':method', 'GET')
        scheme = self.request_headers.get(':scheme', 'https')
        path = self.request_headers.get(':path', '/')
        host = None
        port = None

        if path == '*' or path.startswith("/"):
            first_line_format = "relative"
        elif method == 'CONNECT':  # pragma: no cover
            raise NotImplementedError("CONNECT over HTTP/2 is not implemented.")
        else:  # pragma: no cover
            first_line_format = "absolute"
            # FIXME: verify if path or :host contains what we need
            scheme, host, port, _ = utils.parse_url(path)

        if authority:
            host, _, port = authority.partition(':')

        if not host:
            host = 'localhost'
        if not port:
            port = 443 if scheme == 'https' else 80
        port = int(port)

        data = []
        while self.request_data_queue.qsize() > 0:
            data.append(self.request_data_queue.get())
        data = b"".join(data)

        return HTTPRequest(
            first_line_format,
            method,
            scheme,
            host,
            port,
            path,
            b"HTTP/2.0",
            self.request_headers,
            data,
            timestamp_start=self.timestamp_start,
            timestamp_end=self.timestamp_end,
        )

    def send_request(self, message):
        if self.pushed:
            # nothing to do here
            return

        with self.server_conn.h2.lock:
            # We must not assign a stream id if we are already a zombie.
            if self.zombie:
                return

            self.server_stream_id = self.server_conn.h2.get_next_available_stream_id()
            self.server_to_client_stream_ids[self.server_stream_id] = self.client_stream_id

            self.server_conn.h2.safe_send_headers(
                self.is_zombie,
                self.server_stream_id,
                message.headers
            )
        self.server_conn.h2.safe_send_body(
            self.is_zombie,
            self.server_stream_id,
            message.body
        )

    def read_response_headers(self):
        self.response_arrived.wait()

        status_code = int(self.response_headers.get(':status', 502))

        return HTTPResponse(
            http_version=b"HTTP/2.0",
            status_code=status_code,
            reason='',
            headers=self.response_headers,
            content=None,
            timestamp_start=self.timestamp_start,
            timestamp_end=self.timestamp_end,
        )

    def read_response_body(self, request, response):
        while True:
            try:
                yield self.response_data_queue.get(timeout=1)
            except queue.Empty:
                pass
            if self.response_data_finished.is_set():
                while self.response_data_queue.qsize() > 0:
                    yield self.response_data_queue.get()
                return
            if self.zombie:
                return

    def send_response_headers(self, response):
        self.client_conn.h2.safe_send_headers(
            self.is_zombie,
            self.client_stream_id,
            response.headers
        )

    def send_response_body(self, _response, chunks):
        self.client_conn.h2.safe_send_body(
            self.is_zombie,
            self.client_stream_id,
            chunks
        )

    def check_close_connection(self, flow):
        # This layer only handles a single stream.
        # RFC 7540 8.1: An HTTP request/response exchange fully consumes a single stream.
        return True

    def connect(self):  # pragma: no cover
        raise ValueError("CONNECT inside an HTTP2 stream is not supported.")

    def set_server(self, *args, **kwargs):  # pragma: no cover
        # do not mess with the server connection - all streams share it.
        pass

    def run(self):
        layer = HttpLayer(self, self.mode)
        layer()
        self.zombie = time.time()
