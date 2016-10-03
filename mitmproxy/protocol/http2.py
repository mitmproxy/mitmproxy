from __future__ import absolute_import, print_function, division

import threading
import time
import traceback
import functools

import h2.exceptions
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

    def safe_send_headers(self, raise_zombie, stream_id, headers, **kwargs):
        with self.lock:
            raise_zombie()
            self.send_headers(stream_id, headers.fields, **kwargs)
            self.conn.send(self.data_to_send())

    def safe_send_body(self, raise_zombie, stream_id, chunks):
        for chunk in chunks:
            position = 0
            while position < len(chunk):
                self.lock.acquire()
                raise_zombie(self.lock.release)
                max_outbound_frame_size = self.max_outbound_frame_size
                frame_chunk = chunk[position:position + max_outbound_frame_size]
                if self.local_flow_control_window(stream_id) < len(frame_chunk):
                    self.lock.release()
                    time.sleep(0.1)
                    continue
                self.send_data(stream_id, frame_chunk)
                try:
                    self.conn.send(self.data_to_send())
                except Exception as e:  # pragma: no cover
                    raise e
                finally:
                    self.lock.release()
                position += max_outbound_frame_size
        with self.lock:
            raise_zombie()
            self.end_stream(stream_id)
            self.conn.send(self.data_to_send())


class Http2Layer(base.Layer):

    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.streams = dict()
        self.server_to_client_stream_ids = dict([(0, 0)])
        self.client_conn.h2 = SafeH2Connection(self.client_conn, client_side=False, header_encoding=False)

    def _initiate_server_conn(self):
        if self.server_conn:
            self.server_conn.h2 = SafeH2Connection(self.server_conn, client_side=True, header_encoding=False)
            self.server_conn.h2.initiate_connection()
            self.server_conn.send(self.server_conn.h2.data_to_send())

    def _complete_handshake(self):
        preamble = self.client_conn.rfile.read(24)
        self.client_conn.h2.initiate_connection()
        self.client_conn.h2.receive_data(preamble)
        self.client_conn.send(self.client_conn.h2.data_to_send())

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

        eid = None
        if hasattr(event, 'stream_id'):
            if is_server and event.stream_id % 2 == 1:
                eid = self.server_to_client_stream_ids[event.stream_id]
            else:
                eid = event.stream_id

        if isinstance(event, events.RequestReceived):
            return self._handle_request_received(eid, event, source_conn.h2)
        elif isinstance(event, events.ResponseReceived):
            return self._handle_response_received(eid, event)
        elif isinstance(event, events.DataReceived):
            return self._handle_data_received(eid, event, source_conn)
        elif isinstance(event, events.StreamEnded):
            return self._handle_stream_ended(eid)
        elif isinstance(event, events.StreamReset):
            return self._handle_stream_reset(eid, event, is_server, other_conn)
        elif isinstance(event, events.RemoteSettingsChanged):
            return self._handle_remote_settings_changed(event, other_conn)
        elif isinstance(event, events.ConnectionTerminated):
            return self._handle_connection_terminated(event, is_server)
        elif isinstance(event, events.PushedStreamReceived):
            return self._handle_pushed_stream_received(event, source_conn.h2)
        elif isinstance(event, events.PriorityUpdated):
            return self._handle_priority_updated(eid, event)
        elif isinstance(event, events.TrailersReceived):
            raise NotImplementedError('TrailersReceived not implemented')

        # fail-safe for unhandled events
        return True

    def _handle_request_received(self, eid, event, h2_connection):
        headers = netlib.http.Headers([[k, v] for k, v in event.headers])
        self.streams[eid] = Http2SingleStreamLayer(self, h2_connection, eid, headers)
        self.streams[eid].timestamp_start = time.time()
        self.streams[eid].no_body = (event.stream_ended is not None)
        if event.priority_updated is not None:
            self.streams[eid].priority_exclusive = event.priority_updated.exclusive
            self.streams[eid].priority_depends_on = event.priority_updated.depends_on
            self.streams[eid].priority_weight = event.priority_updated.weight
            self.streams[eid].handled_priority_event = event.priority_updated
        self.streams[eid].start()
        self.streams[eid].request_arrived.set()
        return True

    def _handle_response_received(self, eid, event):
        headers = netlib.http.Headers([[k, v] for k, v in event.headers])
        self.streams[eid].queued_data_length = 0
        self.streams[eid].timestamp_start = time.time()
        self.streams[eid].response_headers = headers
        self.streams[eid].response_arrived.set()
        return True

    def _handle_data_received(self, eid, event, source_conn):
        bsl = self.config.options.body_size_limit
        if bsl and self.streams[eid].queued_data_length > bsl:
            self.streams[eid].kill()
            source_conn.h2.safe_reset_stream(
                event.stream_id,
                h2.errors.REFUSED_STREAM
            )
            self.log("HTTP body too large. Limit is {}.".format(bsl), "info")
        else:
            self.streams[eid].data_queue.put(event.data)
            self.streams[eid].queued_data_length += len(event.data)
            source_conn.h2.safe_increment_flow_control(
                event.stream_id,
                event.flow_controlled_length
            )
        return True

    def _handle_stream_ended(self, eid):
        self.streams[eid].timestamp_end = time.time()
        self.streams[eid].data_finished.set()
        return True

    def _handle_stream_reset(self, eid, event, is_server, other_conn):
        self.streams[eid].kill()
        if eid in self.streams and event.error_code == h2.errors.CANCEL:
            if is_server:
                other_stream_id = self.streams[eid].client_stream_id
            else:
                other_stream_id = self.streams[eid].server_stream_id
            if other_stream_id is not None:
                other_conn.h2.safe_reset_stream(other_stream_id, event.error_code)
        return True

    def _handle_remote_settings_changed(self, event, other_conn):
        new_settings = dict([(key, cs.new_value) for (key, cs) in six.iteritems(event.changed_settings)])
        other_conn.h2.safe_update_settings(new_settings)
        return True

    def _handle_connection_terminated(self, event, is_server):
        self.log("HTTP/2 connection terminated by {}: error code: {}, last stream id: {}, additional data: {}".format(
            "server" if is_server else "client",
            event.error_code,
            event.last_stream_id,
            event.additional_data), "info")

        if event.error_code != h2.errors.NO_ERROR:
            # Something terrible has happened - kill everything!
            self.client_conn.h2.close_connection(
                error_code=event.error_code,
                last_stream_id=event.last_stream_id,
                additional_data=event.additional_data
            )
            self.client_conn.send(self.client_conn.h2.data_to_send())
            self._kill_all_streams()
        else:
            """
            Do not immediately terminate the other connection.
            Some streams might be still sending data to the client.
            """
        return False

    def _handle_pushed_stream_received(self, event, h2_connection):
        # pushed stream ids should be unique and not dependent on race conditions
        # only the parent stream id must be looked up first
        parent_eid = self.server_to_client_stream_ids[event.parent_stream_id]
        with self.client_conn.h2.lock:
            self.client_conn.h2.push_stream(parent_eid, event.pushed_stream_id, event.headers)
            self.client_conn.send(self.client_conn.h2.data_to_send())

        headers = netlib.http.Headers([[k, v] for k, v in event.headers])
        self.streams[event.pushed_stream_id] = Http2SingleStreamLayer(self, h2_connection, event.pushed_stream_id, headers)
        self.streams[event.pushed_stream_id].timestamp_start = time.time()
        self.streams[event.pushed_stream_id].pushed = True
        self.streams[event.pushed_stream_id].parent_stream_id = parent_eid
        self.streams[event.pushed_stream_id].timestamp_end = time.time()
        self.streams[event.pushed_stream_id].request_arrived.set()
        self.streams[event.pushed_stream_id].request_data_finished.set()
        self.streams[event.pushed_stream_id].start()
        return True

    def _handle_priority_updated(self, eid, event):
        if eid in self.streams and self.streams[eid].handled_priority_event is event:
            # this event was already handled during stream creation
            # HeadersFrame + Priority information as RequestReceived
            return True

        with self.server_conn.h2.lock:
            mapped_stream_id = event.stream_id
            if mapped_stream_id in self.streams and self.streams[mapped_stream_id].server_stream_id:
                # if the stream is already up and running and was sent to the server,
                # use the mapped server stream id to update priority information
                mapped_stream_id = self.streams[mapped_stream_id].server_stream_id

            if eid in self.streams:
                self.streams[eid].priority_exclusive = event.exclusive
                self.streams[eid].priority_depends_on = event.depends_on
                self.streams[eid].priority_weight = event.weight

            self.server_conn.h2.prioritize(
                mapped_stream_id,
                weight=event.weight,
                depends_on=self._map_depends_on_stream_id(mapped_stream_id, event.depends_on),
                exclusive=event.exclusive
            )
            self.server_conn.send(self.server_conn.h2.data_to_send())
        return True

    def _map_depends_on_stream_id(self, stream_id, depends_on):
        mapped_depends_on = depends_on
        if mapped_depends_on in self.streams and self.streams[mapped_depends_on].server_stream_id:
            # if the depends-on-stream is already up and running and was sent to the server
            # use the mapped server stream id to update priority information
            mapped_depends_on = self.streams[mapped_depends_on].server_stream_id
        if stream_id == mapped_depends_on:
            # looks like one of the streams wasn't opened yet
            # prevent self-dependent streams which result in ProtocolError
            mapped_depends_on += 2
        return mapped_depends_on

    def _cleanup_streams(self):
        death_time = time.time() - 10

        zombie_streams = [(stream_id, stream) for stream_id, stream in list(self.streams.items()) if stream.zombie]
        outdated_streams = [stream_id for stream_id, stream in zombie_streams if stream.zombie <= death_time]

        for stream_id in outdated_streams:  # pragma: no cover
            self.streams.pop(stream_id, None)

    def _kill_all_streams(self):
        for stream in self.streams.values():
            stream.kill()

    def __call__(self):
        self._initiate_server_conn()
        self._complete_handshake()

        client = self.client_conn.connection
        server = self.server_conn.connection
        conns = [client, server]

        try:
            while True:
                r = tcp.ssl_read_select(conns, 1)
                for conn in r:
                    source_conn = self.client_conn if conn == client else self.server_conn
                    other_conn = self.server_conn if conn == client else self.client_conn
                    is_server = (conn == self.server_conn.connection)

                    with source_conn.h2.lock:
                        try:
                            raw_frame = b''.join(http2.read_raw_frame(source_conn.rfile))
                        except:
                            # read frame failed: connection closed
                            self._kill_all_streams()
                            return

                        if source_conn.h2.state_machine.state == h2.connection.ConnectionState.CLOSED:
                            self.log("HTTP/2 connection entered closed state already", "debug")
                            return

                        incoming_events = source_conn.h2.receive_data(raw_frame)
                        source_conn.send(source_conn.h2.data_to_send())

                        for event in incoming_events:
                            if not self._handle_event(event, source_conn, other_conn, is_server):
                                # connection terminated: GoAway
                                self._kill_all_streams()
                                return

                    self._cleanup_streams()
        except Exception as e:  # pragma: no cover
            self.log(repr(e), "info")
            self.log(traceback.format_exc(), "debug")
            self._kill_all_streams()


def detect_zombie_stream(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.raise_zombie()
        result = func(self, *args, **kwargs)
        self.raise_zombie()
        return result

    return wrapper


class Http2SingleStreamLayer(http._HttpTransmissionLayer, basethread.BaseThread):

    def __init__(self, ctx, h2_connection, stream_id, request_headers):
        super(Http2SingleStreamLayer, self).__init__(
            ctx, name="Http2SingleStreamLayer-{}".format(stream_id)
        )
        self.h2_connection = h2_connection
        self.zombie = None
        self.client_stream_id = stream_id
        self.server_stream_id = None
        self.request_headers = request_headers
        self.response_headers = None
        self.pushed = False

        self.timestamp_start = None
        self.timestamp_end = None

        self.request_arrived = threading.Event()
        self.request_data_queue = queue.Queue()
        self.request_queued_data_length = 0
        self.request_data_finished = threading.Event()

        self.response_arrived = threading.Event()
        self.response_data_queue = queue.Queue()
        self.response_queued_data_length = 0
        self.response_data_finished = threading.Event()

        self.no_body = False

        self.priority_exclusive = None
        self.priority_depends_on = None
        self.priority_weight = None
        self.handled_priority_event = None

    def kill(self):
        if not self.zombie:
            self.zombie = time.time()
            self.request_data_finished.set()
            self.request_arrived.set()
            self.response_arrived.set()
            self.response_data_finished.set()

    def connect(self):  # pragma: no cover
        raise exceptions.Http2ProtocolException("HTTP2 layer should already have a connection.")

    def disconnect(self):  # pragma: no cover
        raise exceptions.Http2ProtocolException("Cannot dis- or reconnect in HTTP2 connections.")

    def set_server(self, address):  # pragma: no cover
        raise exceptions.SetServerNotAllowedException(repr(address))

    def check_close_connection(self, flow):
        # This layer only handles a single stream.
        # RFC 7540 8.1: An HTTP request/response exchange fully consumes a single stream.
        return True

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

    def raise_zombie(self, pre_command=None):
        connection_closed = self.h2_connection.state_machine.state == h2.connection.ConnectionState.CLOSED
        if self.zombie is not None or not hasattr(self.server_conn, 'h2') or connection_closed:
            if pre_command is not None:
                pre_command()
            raise exceptions.Http2ZombieException("Connection already dead")

    @detect_zombie_stream
    def read_request_headers(self):
        self.request_arrived.wait()
        self.raise_zombie()
        first_line_format, method, scheme, host, port, path = http2.parse_headers(self.request_headers)
        return models.HTTPRequest(
            first_line_format,
            method,
            scheme,
            host,
            port,
            path,
            b"HTTP/2.0",
            self.request_headers,
            None,
            timestamp_start=self.timestamp_start,
            timestamp_end=self.timestamp_end,
        )

    @detect_zombie_stream
    def read_request_body(self, request):
        self.request_data_finished.wait()
        data = []
        while self.request_data_queue.qsize() > 0:
            data.append(self.request_data_queue.get())
        return data

    @detect_zombie_stream
    def send_request(self, message):
        if self.pushed:
            # nothing to do here
            return

        while True:
            self.raise_zombie()
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
        self.raise_zombie()

        self.server_stream_id = self.server_conn.h2.get_next_available_stream_id()
        self.server_to_client_stream_ids[self.server_stream_id] = self.client_stream_id

        headers = message.headers.copy()
        headers.insert(0, ":path", message.path)
        headers.insert(0, ":method", message.method)
        headers.insert(0, ":scheme", message.scheme)

        priority_exclusive = None
        priority_depends_on = None
        priority_weight = None
        if self.handled_priority_event:
            # only send priority information if they actually came with the original HeadersFrame
            # and not if they got updated before/after with a PriorityFrame
            priority_exclusive = self.priority_exclusive
            priority_depends_on = self._map_depends_on_stream_id(self.server_stream_id, self.priority_depends_on)
            priority_weight = self.priority_weight

        try:
            self.server_conn.h2.safe_send_headers(
                self.raise_zombie,
                self.server_stream_id,
                headers,
                end_stream=self.no_body,
                priority_exclusive=priority_exclusive,
                priority_depends_on=priority_depends_on,
                priority_weight=priority_weight,
            )
        except Exception as e:  # pragma: no cover
            raise e
        finally:
            self.raise_zombie()
            self.server_conn.h2.lock.release()

        if not self.no_body:
            self.server_conn.h2.safe_send_body(
                self.raise_zombie,
                self.server_stream_id,
                [message.body]
            )

    @detect_zombie_stream
    def read_response_headers(self):
        self.response_arrived.wait()

        self.raise_zombie()

        status_code = int(self.response_headers.get(':status', 502))
        headers = self.response_headers.copy()
        headers.pop(":status", None)

        return models.HTTPResponse(
            http_version=b"HTTP/2.0",
            status_code=status_code,
            reason=b'',
            headers=headers,
            content=None,
            timestamp_start=self.timestamp_start,
            timestamp_end=self.timestamp_end,
        )

    @detect_zombie_stream
    def read_response_body(self, request, response):
        while True:
            try:
                yield self.response_data_queue.get(timeout=1)
            except queue.Empty:  # pragma: no cover
                pass
            if self.response_data_finished.is_set():
                self.raise_zombie()
                while self.response_data_queue.qsize() > 0:
                    yield self.response_data_queue.get()
                break
            self.raise_zombie()

    @detect_zombie_stream
    def send_response_headers(self, response):
        headers = response.headers.copy()
        headers.insert(0, ":status", str(response.status_code))
        for forbidden_header in h2.utilities.CONNECTION_HEADERS:
            if forbidden_header in headers:
                del headers[forbidden_header]
        with self.client_conn.h2.lock:
            self.client_conn.h2.safe_send_headers(
                self.raise_zombie,
                self.client_stream_id,
                headers
            )

    @detect_zombie_stream
    def send_response_body(self, _response, chunks):
        self.client_conn.h2.safe_send_body(
            self.raise_zombie,
            self.client_stream_id,
            chunks
        )

    def __call__(self):
        raise EnvironmentError('Http2SingleStreamLayer must be run as thread')

    def run(self):
        layer = http.HttpLayer(self, self.mode)

        try:
            layer()
        except exceptions.Http2ZombieException as e:  # pragma: no cover
            pass
        except exceptions.ProtocolException as e:  # pragma: no cover
            self.log(repr(e), "info")
            self.log(traceback.format_exc(), "debug")
        except exceptions.SetServerNotAllowedException as e:  # pragma: no cover
            self.log("Changing the Host server for HTTP/2 connections not allowed: {}".format(e), "info")
        except exceptions.Kill:
            self.log("Connection killed", "info")

        self.kill()
