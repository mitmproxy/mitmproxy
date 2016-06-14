from __future__ import absolute_import, print_function, division

import threading
import time
import traceback

import h2.exceptions
import hyperframe
import six
from h2 import connection
from h2 import events
from six.moves import queue

import netlib.exceptions
from mitmproxy import exceptions
from mitmproxy import models
from mitmproxy.protocol import base
from mitmproxy.protocol import http
import netlib.http
from netlib import tcp
from netlib import basethread
from netlib.http import http2


class SafeH2Connection(connection.H2Connection):

    def __init__(self, conn, *args, **kwargs):
        super(SafeH2Connection, self).__init__(*args, **kwargs)
        self.conn = conn
        self.lock = threading.RLock()

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
            except h2.exceptions.StreamClosedError:  # pragma: no cover
                # stream is already closed - good
                pass
            self.conn.send(self.data_to_send())

    def safe_update_settings(self, new_settings):
        with self.lock:
            self.update_settings(new_settings)
            self.conn.send(self.data_to_send())

    def safe_send_headers(self, is_zombie, stream_id, headers):
        # make sure to have a lock
        if is_zombie():  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")
        self.send_headers(stream_id, headers.fields)
        self.conn.send(self.data_to_send())

    def safe_send_body(self, is_zombie, stream_id, chunks):
        for chunk in chunks:
            position = 0
            while position < len(chunk):
                self.lock.acquire()
                if is_zombie():  # pragma: no cover
                    self.lock.release()
                    raise exceptions.Http2ProtocolException("Zombie Stream")
                max_outbound_frame_size = self.max_outbound_frame_size
                frame_chunk = chunk[position:position + max_outbound_frame_size]
                if self.local_flow_control_window(stream_id) < len(frame_chunk):
                    self.lock.release()
                    time.sleep(0.1)
                    continue
                self.send_data(stream_id, frame_chunk)
                try:
                    self.conn.send(self.data_to_send())
                except Exception as e:
                    raise e
                finally:
                    self.lock.release()
                position += max_outbound_frame_size
        with self.lock:
            if is_zombie():  # pragma: no cover
                raise exceptions.Http2ProtocolException("Zombie Stream")
            self.end_stream(stream_id)
            self.conn.send(self.data_to_send())


class Http2Layer(base.Layer):

    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.streams = dict()
        self.server_to_client_stream_ids = dict([(0, 0)])
        self.client_conn.h2 = SafeH2Connection(self.client_conn, client_side=False, header_encoding=False)

        # make sure that we only pass actual SSL.Connection objects in here,
        # because otherwise ssl_read_select fails!
        self.active_conns = [self.client_conn.connection]

    def _initiate_server_conn(self):
        self.server_conn.h2 = SafeH2Connection(self.server_conn, client_side=True, header_encoding=False)
        self.server_conn.h2.initiate_connection()
        self.server_conn.send(self.server_conn.h2.data_to_send())
        self.active_conns.append(self.server_conn.connection)

    def connect(self):  # pragma: no cover
        raise exceptions.Http2ProtocolException("HTTP2 layer should already have a connection.")

    def set_server(self):  # pragma: no cover
        raise exceptions.Http2ProtocolException("Cannot change server for HTTP2 connections.")

    def disconnect(self):  # pragma: no cover
        raise exceptions.Http2ProtocolException("Cannot dis- or reconnect in HTTP2 connections.")

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

        if isinstance(event, events.RequestReceived):
            headers = netlib.http.Headers([[k, v] for k, v in event.headers])
            self.streams[eid] = Http2SingleStreamLayer(self, eid, headers)
            self.streams[eid].timestamp_start = time.time()
            self.streams[eid].start()
        elif isinstance(event, events.ResponseReceived):
            headers = netlib.http.Headers([[k, v] for k, v in event.headers])
            self.streams[eid].queued_data_length = 0
            self.streams[eid].timestamp_start = time.time()
            self.streams[eid].response_headers = headers
            self.streams[eid].response_arrived.set()
        elif isinstance(event, events.DataReceived):
            if self.config.body_size_limit and self.streams[eid].queued_data_length > self.config.body_size_limit:
                raise netlib.exceptions.HttpException("HTTP body too large. Limit is {}.".format(self.config.body_size_limit))
            self.streams[eid].data_queue.put(event.data)
            self.streams[eid].queued_data_length += len(event.data)
            source_conn.h2.safe_increment_flow_control(event.stream_id, event.flow_controlled_length)
        elif isinstance(event, events.StreamEnded):
            self.streams[eid].timestamp_end = time.time()
            self.streams[eid].data_finished.set()
        elif isinstance(event, events.StreamReset):
            self.streams[eid].zombie = time.time()
            if eid in self.streams and event.error_code == 0x8:
                if is_server:
                    other_stream_id = self.streams[eid].client_stream_id
                else:
                    other_stream_id = self.streams[eid].server_stream_id
                if other_stream_id is not None:
                    other_conn.h2.safe_reset_stream(other_stream_id, event.error_code)
        elif isinstance(event, events.RemoteSettingsChanged):
            new_settings = dict([(id, cs.new_value) for (id, cs) in six.iteritems(event.changed_settings)])
            other_conn.h2.safe_update_settings(new_settings)
        elif isinstance(event, events.ConnectionTerminated):
            if event.error_code == h2.errors.NO_ERROR:
                # Do not immediately terminate the other connection.
                # Some streams might be still sending data to the client.
                return False
            else:
                # Something terrible has happened - kill everything!
                self.client_conn.h2.close_connection(
                    error_code=event.error_code,
                    last_stream_id=event.last_stream_id,
                    additional_data=event.additional_data
                )
                self.client_conn.send(self.client_conn.h2.data_to_send())
                self._kill_all_streams()
                return False

        elif isinstance(event, events.PushedStreamReceived):
            # pushed stream ids should be unique and not dependent on race conditions
            # only the parent stream id must be looked up first
            parent_eid = self.server_to_client_stream_ids[event.parent_stream_id]
            with self.client_conn.h2.lock:
                self.client_conn.h2.push_stream(parent_eid, event.pushed_stream_id, event.headers)
                self.client_conn.send(self.client_conn.h2.data_to_send())

            headers = netlib.http.Headers([[str(k), str(v)] for k, v in event.headers])
            self.streams[event.pushed_stream_id] = Http2SingleStreamLayer(self, event.pushed_stream_id, headers)
            self.streams[event.pushed_stream_id].timestamp_start = time.time()
            self.streams[event.pushed_stream_id].pushed = True
            self.streams[event.pushed_stream_id].parent_stream_id = parent_eid
            self.streams[event.pushed_stream_id].timestamp_end = time.time()
            self.streams[event.pushed_stream_id].request_data_finished.set()
            self.streams[event.pushed_stream_id].start()
        elif isinstance(event, events.PriorityUpdated):
            stream_id = event.stream_id
            if stream_id in self.streams.keys() and self.streams[stream_id].server_stream_id:
                stream_id = self.streams[stream_id].server_stream_id

            depends_on = event.depends_on
            if depends_on in self.streams.keys() and self.streams[depends_on].server_stream_id:
                depends_on = self.streams[depends_on].server_stream_id

            # weight is between 1 and 256 (inclusive), but represented as uint8 (0 to 255)
            frame = hyperframe.frame.PriorityFrame(stream_id, depends_on, event.weight - 1, event.exclusive)
            self.server_conn.send(frame.serialize())
        elif isinstance(event, events.TrailersReceived):
            raise NotImplementedError()

        return True

    def _cleanup_streams(self):
        death_time = time.time() - 10
        for stream_id in self.streams.keys():
            zombie = self.streams[stream_id].zombie
            if zombie and zombie <= death_time:
                self.streams.pop(stream_id, None)

    def _kill_all_streams(self):
        for stream in self.streams.values():
            if not stream.zombie:
                stream.zombie = time.time()
                stream.request_data_finished.set()
                stream.response_arrived.set()
                stream.data_finished.set()

    def __call__(self):
        if self.server_conn:
            self._initiate_server_conn()

        preamble = self.client_conn.rfile.read(24)
        self.client_conn.h2.initiate_connection()
        self.client_conn.h2.receive_data(preamble)
        self.client_conn.send(self.client_conn.h2.data_to_send())

        try:
            while True:
                r = tcp.ssl_read_select(self.active_conns, 1)
                for conn in r:
                    source_conn = self.client_conn if conn == self.client_conn.connection else self.server_conn
                    other_conn = self.server_conn if conn == self.client_conn.connection else self.client_conn
                    is_server = (conn == self.server_conn.connection)

                    with source_conn.h2.lock:
                        try:
                            raw_frame = b''.join(http2.framereader.http2_read_raw_frame(source_conn.rfile))
                        except:
                            # read frame failed: connection closed
                            self._kill_all_streams()
                            return

                        incoming_events = source_conn.h2.receive_data(raw_frame)
                        source_conn.send(source_conn.h2.data_to_send())

                        for event in incoming_events:
                            if not self._handle_event(event, source_conn, other_conn, is_server):
                                # connection terminated: GoAway
                                self._kill_all_streams()
                                return

                self._cleanup_streams()
        except Exception as e:
            self.log(repr(e), "info")
            self.log(traceback.format_exc(), "debug")
            self._kill_all_streams()


class Http2SingleStreamLayer(http._HttpTransmissionLayer, basethread.BaseThread):

    def __init__(self, ctx, stream_id, request_headers):
        super(Http2SingleStreamLayer, self).__init__(
            ctx, name="Http2SingleStreamLayer-{}".format(stream_id)
        )
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
        self.request_queued_data_length = v

    def is_zombie(self):
        return self.zombie is not None

    def read_request(self):
        self.request_data_finished.wait()

        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

        authority = self.request_headers.get(':authority', '')
        method = self.request_headers.get(':method', 'GET')
        scheme = self.request_headers.get(':scheme', 'https')
        path = self.request_headers.get(':path', '/')
        self.request_headers.clear(":method")
        self.request_headers.clear(":scheme")
        self.request_headers.clear(":path")
        host = None
        port = None

        if path == '*' or path.startswith("/"):
            first_line_format = "relative"
        elif method == 'CONNECT':  # pragma: no cover
            raise NotImplementedError("CONNECT over HTTP/2 is not implemented.")
        else:  # pragma: no cover
            first_line_format = "absolute"
            # FIXME: verify if path or :host contains what we need
            scheme, host, port, _ = netlib.http.url.parse(path)

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

        return models.HTTPRequest(
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

    def read_request_body(self, request):  # pragma: no cover
        raise NotImplementedError()

    def send_request(self, message):
        if self.pushed:
            # nothing to do here
            return

        while True:
            if self.zombie:  # pragma: no cover
                raise exceptions.Http2ProtocolException("Zombie Stream")

            self.server_conn.h2.lock.acquire()

            max_streams = self.server_conn.h2.remote_settings.max_concurrent_streams
            if self.server_conn.h2.open_outbound_streams + 1 >= max_streams:
                # wait until we get a free slot for a new outgoing stream
                self.server_conn.h2.lock.release()
                time.sleep(0.1)
                continue

            # keep the lock
            break

        # We must not assign a stream id if we are already a zombie.
        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

        self.server_stream_id = self.server_conn.h2.get_next_available_stream_id()
        self.server_to_client_stream_ids[self.server_stream_id] = self.client_stream_id

        headers = message.headers.copy()
        headers.insert(0, ":path", message.path)
        headers.insert(0, ":method", message.method)
        headers.insert(0, ":scheme", message.scheme)
        self.server_stream_id = self.server_conn.h2.get_next_available_stream_id()
        self.server_to_client_stream_ids[self.server_stream_id] = self.client_stream_id

        try:
            self.server_conn.h2.safe_send_headers(
                self.is_zombie,
                self.server_stream_id,
                headers,
            )
        except Exception as e:
            raise e
        finally:
            self.server_conn.h2.lock.release()

        self.server_conn.h2.safe_send_body(
            self.is_zombie,
            self.server_stream_id,
            message.body
        )
        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

    def read_response_headers(self):
        self.response_arrived.wait()

        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

        status_code = int(self.response_headers.get(':status', 502))
        headers = self.response_headers.copy()
        headers.clear(":status")

        return models.HTTPResponse(
            http_version=b"HTTP/2.0",
            status_code=status_code,
            reason='',
            headers=headers,
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
                if self.zombie:  # pragma: no cover
                    raise exceptions.Http2ProtocolException("Zombie Stream")
                while self.response_data_queue.qsize() > 0:
                    yield self.response_data_queue.get()
                break
            if self.zombie:  # pragma: no cover
                raise exceptions.Http2ProtocolException("Zombie Stream")

    def send_response_headers(self, response):
        headers = response.headers.copy()
        headers.insert(0, ":status", str(response.status_code))
        with self.client_conn.h2.lock:
            self.client_conn.h2.safe_send_headers(
                self.is_zombie,
                self.client_stream_id,
                headers
            )
        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

    def send_response_body(self, _response, chunks):
        self.client_conn.h2.safe_send_body(
            self.is_zombie,
            self.client_stream_id,
            chunks
        )
        if self.zombie:  # pragma: no cover
            raise exceptions.Http2ProtocolException("Zombie Stream")

    def check_close_connection(self, flow):
        # This layer only handles a single stream.
        # RFC 7540 8.1: An HTTP request/response exchange fully consumes a single stream.
        return True

    def set_server(self, *args, **kwargs):  # pragma: no cover
        # do not mess with the server connection - all streams share it.
        pass

    def run(self):
        self()

    def __call__(self):
        layer = http.HttpLayer(self, self.mode)

        try:
            layer()
        except exceptions.ProtocolException as e:
            self.log(repr(e), "info")
            self.log(traceback.format_exc(), "debug")

        if not self.zombie:
            self.zombie = time.time()
