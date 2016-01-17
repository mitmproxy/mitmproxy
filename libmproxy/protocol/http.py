from __future__ import (absolute_import, print_function, division)

import sys
import traceback
import six
import struct
import threading
import time
import Queue

from netlib import tcp
from netlib.exceptions import HttpException, HttpReadDisconnect, NetlibException
from netlib.http import http1, Headers, CONTENT_MISSING
from netlib.tcp import Address, ssl_read_select

import h2
from h2.connection import H2Connection
from h2.events import *
from hyperframe import frame

from .base import Layer, Kill
from .. import utils
from ..exceptions import HttpProtocolException, ProtocolException
from ..models import (
    HTTPFlow,
    HTTPRequest,
    HTTPResponse,
    make_error_response,
    make_connect_response,
    Error,
    expect_continue_response
)


class _HttpLayer(Layer):
    def read_request(self):
        raise NotImplementedError()

    def read_request_body(self, request):
        raise NotImplementedError()

    def send_request(self, request):
        raise NotImplementedError()

    def read_response(self, request):
        response = self.read_response_headers()
        response.data.content = b"".join(
            self.read_response_body(request, response)
        )
        return response

    def read_response_headers(self):
        raise NotImplementedError()

    def read_response_body(self, request, response):
        raise NotImplementedError()
        yield "this is a generator"  # pragma: no cover

    def send_response(self, response):
        if response.content == CONTENT_MISSING:
            raise HttpException("Cannot assemble flow with CONTENT_MISSING")
        self.send_response_headers(response)
        self.send_response_body(response, [response.content])

    def send_response_headers(self, response):
        raise NotImplementedError()

    def send_response_body(self, response, chunks):
        raise NotImplementedError()

    def check_close_connection(self, flow):
        raise NotImplementedError()


class Http1Layer(_HttpLayer):
    def __init__(self, ctx, mode):
        super(Http1Layer, self).__init__(ctx)
        self.mode = mode

    def read_request(self):
        req = http1.read_request(self.client_conn.rfile, body_size_limit=self.config.body_size_limit)
        return HTTPRequest.wrap(req)

    def read_request_body(self, request):
        expected_size = http1.expected_http_body_size(request)
        return http1.read_body(self.client_conn.rfile, expected_size, self.config.body_size_limit)

    def send_request(self, request):
        self.server_conn.wfile.write(http1.assemble_request(request))
        self.server_conn.wfile.flush()

    def read_response_headers(self):
        resp = http1.read_response_head(self.server_conn.rfile)
        return HTTPResponse.wrap(resp)

    def read_response_body(self, request, response):
        expected_size = http1.expected_http_body_size(request, response)
        return http1.read_body(self.server_conn.rfile, expected_size, self.config.body_size_limit)

    def send_response_headers(self, response):
        raw = http1.assemble_response_head(response)
        self.client_conn.wfile.write(raw)
        self.client_conn.wfile.flush()

    def send_response_body(self, response, chunks):
        for chunk in http1.assemble_body(response.headers, chunks):
            self.client_conn.wfile.write(chunk)
            self.client_conn.wfile.flush()

    def check_close_connection(self, flow):
        request_close = http1.connection_close(
            flow.request.http_version,
            flow.request.headers
        )
        response_close = http1.connection_close(
            flow.response.http_version,
            flow.response.headers
        )
        read_until_eof = http1.expected_http_body_size(flow.request, flow.response) == -1
        close_connection = request_close or response_close or read_until_eof
        if flow.request.form_in == "authority" and flow.response.status_code == 200:
            # Workaround for https://github.com/mitmproxy/mitmproxy/issues/313:
            # Charles Proxy sends a CONNECT response with HTTP/1.0
            # and no Content-Length header

            return False
        return close_connection

    def __call__(self):
        layer = HttpLayer(self, self.mode)
        layer()


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
            except h2.exceptions.ProtocolError:
                # stream is already closed - good
                pass
            self.conn.send(self.data_to_send())

    def safe_acknowledge_settings(self, event):
        with self.conn.h2.lock:
            self.conn.h2.acknowledge_settings(event)
            self.conn.send(self.data_to_send())

    def safe_update_settings(self, new_settings):
        with self.conn.h2.lock:
            self.update_settings(new_settings)
            self.conn.send(self.data_to_send())

    def safe_send_headers(self, is_zombie, stream_id, headers):
        with self.lock:
            if is_zombie(self, stream_id):
                return
            self.send_headers(stream_id, headers)
            self.conn.send(self.data_to_send())

    def safe_send_body(self, is_zombie, stream_id, chunks):
        for chunk in chunks:
            position = 0
            while position < len(chunk):
                self.lock.acquire()
                max_outbound_frame_size = self.max_outbound_frame_size
                frame_chunk = chunk[position:position+max_outbound_frame_size]
                if self.local_flow_control_window(stream_id) < len(frame_chunk):
                    self.lock.release()
                    time.sleep(0)
                    continue
                if is_zombie(self, stream_id):
                    return
                self.send_data(stream_id, frame_chunk)
                self.conn.send(self.data_to_send())
                self.lock.release()
                position += max_outbound_frame_size
        with self.lock:
            if is_zombie(self, stream_id):
                return
            self.end_stream(stream_id)
            self.conn.send(self.data_to_send())


class Http2Layer(Layer):
    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.streams = dict()
        self.server_to_client_stream_ids = dict([(0, 0)])
        self.client_conn.h2 = SafeH2Connection(self.client_conn, client_side=False)

        # make sure that we only pass actual SSL.Connection objects in here,
        # because otherwise ssl_read_select fails!
        self.active_conns = [self.client_conn.connection]

    def _initiate_server_conn(self):
        self.server_conn.h2 = SafeH2Connection(self.server_conn, client_side=True)
        self.server_conn.h2.initiate_connection()
        self.server_conn.h2.update_settings({frame.SettingsFrame.ENABLE_PUSH: False})
        self.server_conn.send(self.server_conn.h2.data_to_send())
        self.active_conns.append(self.server_conn.connection)

    def connect(self):
        self.ctx.connect()
        self.server_conn.connect()
        self._initiate_server_conn()

    def set_server(self):
        raise NotImplementedError("Cannot change server for HTTP2 connections.")

    def disconnect(self):
        raise NotImplementedError("Cannot dis- or reconnect in HTTP2 connections.")

    def next_layer(self):
        # WebSockets over HTTP/2?
        # CONNECT for proxying?
        raise NotImplementedError()

    def __call__(self):
        if self.server_conn:
            self._initiate_server_conn()

        preamble = self.client_conn.rfile.read(24)
        self.client_conn.h2.initiate_connection()
        self.client_conn.h2.update_settings({frame.SettingsFrame.ENABLE_PUSH: False})
        self.client_conn.h2.receive_data(preamble)
        self.client_conn.send(self.client_conn.h2.data_to_send())

        while True:
            r = ssl_read_select(self.active_conns, 1)
            for conn in r:
                source_conn = self.client_conn if conn == self.client_conn.connection else self.server_conn
                other_conn = self.server_conn if conn == self.client_conn.connection else self.client_conn
                is_server = (conn == self.server_conn.connection)

                fields = struct.unpack("!HB", source_conn.rfile.peek(3))
                length = (fields[0] << 8) + fields[1]
                raw_frame = source_conn.rfile.safe_read(9 + length)

                with source_conn.h2.lock:
                    events = source_conn.h2.receive_data(raw_frame)
                    source_conn.send(source_conn.h2.data_to_send())

                    for event in events:
                        if hasattr(event, 'stream_id'):
                            if is_server:
                                eid = self.server_to_client_stream_ids[event.stream_id]
                            else:
                                eid = event.stream_id

                        if isinstance(event, RequestReceived):
                            headers = Headers([[str(k), str(v)] for k, v in event.headers])
                            self.streams[eid] = Http2SingleStreamLayer(self, eid, headers)
                            self.streams[eid].timestamp_start = time.time()
                            self.streams[eid].start()
                        elif isinstance(event, ResponseReceived):
                            headers = Headers([[str(k), str(v)] for k, v in event.headers])
                            self.streams[eid].timestamp_start = time.time()
                            self.streams[eid].response_headers = headers
                            self.streams[eid].response_arrived.set()
                        elif isinstance(event, DataReceived):
                            self.streams[eid].data_queue.put(event.data)
                            source_conn.h2.safe_increment_flow_control(event.stream_id, len(event.data))
                        elif isinstance(event, StreamEnded):
                            self.streams[eid].timestamp_end = time.time()
                            self.streams[eid].data_finished.set()
                        elif isinstance(event, StreamReset):
                            self.streams[eid].zombie = time.time()
                            if eid in self.streams and event.error_code == 0x8:
                                if is_server:
                                    other_stream_id = self.streams[eid].client_stream_id
                                else:
                                    other_stream_id = self.streams[eid].server_stream_id
                                other_conn.h2.safe_reset_stream(other_stream_id, event.error_code)
                        elif isinstance(event, RemoteSettingsChanged):
                            source_conn.h2.safe_acknowledge_settings(event)
                            new_settings = dict([(id, cs.new_value) for (id, cs) in event.changed_settings.iteritems()])
                            other_conn.h2.safe_update_settings(new_settings)
                        elif isinstance(event, ConnectionTerminated):
                            other_conn.h2.safe_close_connection(event.error_code)
                            return
                        elif isinstance(event, TrailersReceived):
                            raise NotImplementedError()
                        elif isinstance(event, PushedStreamReceived):
                            raise NotImplementedError()

            death_time = time.time() - 10
            for stream_id in self.streams.keys():
                zombie = self.streams[stream_id].zombie
                if zombie and zombie <= death_time:
                    self.streams.pop(stream_id, None)


class Http2SingleStreamLayer(_HttpLayer, threading.Thread):
    def __init__(self, ctx, stream_id, request_headers):
        super(Http2SingleStreamLayer, self).__init__(ctx)
        self.zombie = None
        self.client_stream_id = stream_id
        self.server_stream_id = None
        self.request_headers = request_headers
        self.response_headers = None
        self.data_queue = Queue.Queue()

        self.response_arrived = threading.Event()
        self.data_finished = threading.Event()

    def is_zombie(self, h2_conn, stream_id):
        if self.zombie:
            return True

        try:
            # TODO: replace private API call
            h2_conn._get_stream_by_id(stream_id)
        except Exception as e:
            if isinstance(e, h2.exceptions.StreamClosedError):
                return true

        return False

    def read_request(self):
        self.data_finished.wait()
        self.data_finished.clear()

        authority = self.request_headers.get(':authority', '')
        method = self.request_headers.get(':method', 'GET')
        scheme = self.request_headers.get(':scheme', 'https')
        path = self.request_headers.get(':path', '/')
        host = None
        port = None

        if path == '*' or path.startswith("/"):
            form_in = "relative"
        elif method == 'CONNECT':
            form_in = "authority"
            if ":" in authority:
                host, port = authority.split(":", 1)
            else:
                host = authority
        else:
            form_in = "absolute"
            # FIXME: verify if path or :host contains what we need
            scheme, host, port, _ = utils.parse_url(path)

        if host is None:
            host = 'localhost'
        if port is None:
            port = 80 if scheme == 'http' else 443
        port = int(port)

        data = []
        while self.data_queue.qsize() > 0:
            data.append(self.data_queue.get())

        return HTTPRequest(
            form_in,
            method,
            scheme,
            host,
            port,
            path,
            (2, 0),
            self.request_headers,
            data,
            timestamp_start=self.timestamp_start,
            timestamp_end=self.timestamp_end,
            form_out=None, # TODO: (request.form_out if hasattr(request, 'form_out') else None),
        )

    def send_request(self, message):
        with self.server_conn.h2.lock:
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
            http_version=(2, 0),
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
                yield self.data_queue.get(timeout=1)
            except Queue.Empty:
                pass
            if self.data_finished.is_set():
                while self.data_queue.qsize() > 0:
                    yield self.data_queue.get()
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

    def connect(self):
        raise ValueError("CONNECT inside an HTTP2 stream is not supported.")

    def set_server(self, *args, **kwargs):
        # do not mess with the server connection - all streams share it.
        pass

    def run(self):
        layer = HttpLayer(self, self.mode)
        layer()
        self.zombie = time.time()


class ConnectServerConnection(object):

    """
    "Fake" ServerConnection to represent state after a CONNECT request to an upstream proxy.
    """

    def __init__(self, address, ctx):
        self.address = tcp.Address.wrap(address)
        self._ctx = ctx

    @property
    def via(self):
        return self._ctx.server_conn

    def __getattr__(self, item):
        return getattr(self.via, item)

    def __nonzero__(self):
        return bool(self.via)


class UpstreamConnectLayer(Layer):

    def __init__(self, ctx, connect_request):
        super(UpstreamConnectLayer, self).__init__(ctx)
        self.connect_request = connect_request
        self.server_conn = ConnectServerConnection(
            (connect_request.host, connect_request.port),
            self.ctx
        )

    def __call__(self):
        layer = self.ctx.next_layer(self)
        layer()

    def _send_connect_request(self):
        self.send_request(self.connect_request)
        resp = self.read_response(self.connect_request)
        if resp.status_code != 200:
            raise ProtocolException("Reconnect: Upstream server refuses CONNECT request")

    def connect(self):
        if not self.server_conn:
            self.ctx.connect()
            self._send_connect_request()
        else:
            pass  # swallow the message

    def change_upstream_proxy_server(self, address):
        if address != self.server_conn.via.address:
            self.ctx.set_server(address)

    def set_server(self, address, server_tls=None, sni=None):
        if self.ctx.server_conn:
            self.ctx.disconnect()
        address = Address.wrap(address)
        self.connect_request.host = address.host
        self.connect_request.port = address.port
        self.server_conn.address = address

        if server_tls:
            raise ProtocolException(
                "Cannot upgrade to TLS, no TLS layer on the protocol stack."
            )


class HttpLayer(Layer):

    def __init__(self, ctx, mode):
        super(HttpLayer, self).__init__(ctx)
        self.mode = mode
        self.__original_server_conn = None
        "Contains the original destination in transparent mode, which needs to be restored"
        "if an inline script modified the target server for a single http request"

    def __call__(self):
        if self.mode == "transparent":
            self.__original_server_conn = self.server_conn
        while True:
            try:
                request = self.get_request_from_client()
                self.log("request", "debug", [repr(request)])

                # Handle Proxy Authentication
                # Proxy Authentication conceptually does not work in transparent mode.
                # We catch this misconfiguration on startup. Here, we sort out requests
                # after a successful CONNECT request (which do not need to be validated anymore)
                if self.mode != "transparent" and not self.authenticate(request):
                    return

                # Make sure that the incoming request matches our expectations
                self.validate_request(request)

                # Regular Proxy Mode: Handle CONNECT
                if self.mode == "regular" and request.form_in == "authority":
                    self.handle_regular_mode_connect(request)
                    return

            except HttpReadDisconnect:
                # don't throw an error for disconnects that happen before/between requests.
                return
            except NetlibException as e:
                self.send_error_response(400, repr(e))
                six.reraise(ProtocolException, ProtocolException(
                    "Error in HTTP connection: %s" % repr(e)), sys.exc_info()[2])

            try:
                flow = HTTPFlow(self.client_conn, self.server_conn, live=self)
                flow.request = request
                self.process_request_hook(flow)

                if not flow.response:
                    self.establish_server_connection(flow)
                    self.get_response_from_server(flow)
                else:
                    # response was set by an inline script.
                    # we now need to emulate the responseheaders hook.
                    flow = self.channel.ask("responseheaders", flow)
                    if flow == Kill:
                        raise Kill()

                self.log("response", "debug", [repr(flow.response)])
                flow = self.channel.ask("response", flow)
                if flow == Kill:
                    raise Kill()
                self.send_response_to_client(flow)

                if self.check_close_connection(flow):
                    return

                # Handle 101 Switching Protocols
                # It may be useful to pass additional args (such as the upgrade header)
                # to next_layer in the future
                if flow.response.status_code == 101:
                    layer = self.ctx.next_layer(self)
                    layer()
                    return

                # Upstream Proxy Mode: Handle CONNECT
                if flow.request.form_in == "authority" and flow.response.status_code == 200:
                    self.handle_upstream_mode_connect(flow.request.copy())
                    return

            except (ProtocolException, NetlibException) as e:
                self.send_error_response(502, repr(e))

                if not flow.response:
                    flow.error = Error(str(e))
                    self.channel.ask("error", flow)
                    self.log(traceback.format_exc(), "debug")
                    return
                else:
                    six.reraise(ProtocolException, ProtocolException(
                        "Error in HTTP connection: %s" % repr(e)), sys.exc_info()[2])
            finally:
                flow.live = False

    def get_request_from_client(self):
        request = self.read_request()
        if request.headers.get("expect", "").lower() == "100-continue":
            # TODO: We may have to use send_response_headers for HTTP2 here.
            self.send_response(expect_continue_response)
            request.headers.pop("expect")
            request.body = b"".join(self.read_request_body(request))
        return request

    def send_error_response(self, code, message):
        try:
            response = make_error_response(code, message)
            self.send_response(response)
        except NetlibException, h2.exceptions.H2Error:
            pass

    def change_upstream_proxy_server(self, address):
        # Make set_upstream_proxy_server always available,
        # even if there's no UpstreamConnectLayer
        if address != self.server_conn.address:
            return self.set_server(address)

    def handle_regular_mode_connect(self, request):
        self.set_server((request.host, request.port))
        self.send_response(make_connect_response(request.http_version))
        layer = self.ctx.next_layer(self)
        layer()

    def handle_upstream_mode_connect(self, connect_request):
        layer = UpstreamConnectLayer(self, connect_request)
        layer()

    def send_response_to_client(self, flow):
        if not flow.response.stream:
            # no streaming:
            # we already received the full response from the server and can
            # send it to the client straight away.
            self.send_response(flow.response)
        else:
            # streaming:
            # First send the headers and then transfer the response incrementally
            self.send_response_headers(flow.response)
            chunks = self.read_response_body(
                flow.request,
                flow.response
            )
            if callable(flow.response.stream):
                chunks = flow.response.stream(chunks)
            self.send_response_body(flow.response, chunks)
            flow.response.timestamp_end = utils.timestamp()

    def get_response_from_server(self, flow):
        def get_response():
            self.send_request(flow.request)
            flow.response = self.read_response_headers()

        try:
            get_response()
        except NetlibException as v:
            self.log(
                "server communication error: %s" % repr(v),
                level="debug"
            )
            # In any case, we try to reconnect at least once. This is
            # necessary because it might be possible that we already
            # initiated an upstream connection after clientconnect that
            # has already been expired, e.g consider the following event
            # log:
            # > clientconnect (transparent mode destination known)
            # > serverconnect (required for client tls handshake)
            # > read n% of large request
            # > server detects timeout, disconnects
            # > read (100-n)% of large request
            # > send large request upstream
            self.disconnect()
            self.connect()
            get_response()

        # call the appropriate script hook - this is an opportunity for an
        # inline script to set flow.stream = True
        flow = self.channel.ask("responseheaders", flow)
        if flow == Kill:
            raise Kill()

        if flow.response.stream:
            flow.response.data.content = CONTENT_MISSING
        else:
            flow.response.data.content = b"".join(self.read_response_body(
                flow.request,
                flow.response
            ))
        flow.response.timestamp_end = utils.timestamp()

        # no further manipulation of self.server_conn beyond this point
        # we can safely set it as the final attribute value here.
        flow.server_conn = self.server_conn

    def process_request_hook(self, flow):
        # Determine .scheme, .host and .port attributes for inline scripts.
        # For absolute-form requests, they are directly given in the request.
        # For authority-form requests, we only need to determine the request scheme.
        # For relative-form requests, we need to determine host and port as
        # well.
        if self.mode == "regular":
            pass  # only absolute-form at this point, nothing to do here.
        elif self.mode == "upstream":
            if flow.request.form_in == "authority":
                flow.request.scheme = "http"  # pseudo value
        else:
            # Setting request.host also updates the host header, which we want to preserve
            host_header = flow.request.headers.get("host", None)
            flow.request.host = self.__original_server_conn.address.host
            flow.request.port = self.__original_server_conn.address.port
            if host_header:
                flow.request.headers["host"] = host_header
            # TODO: This does not really work if we change the first request and --no-upstream-cert is enabled
            flow.request.scheme = "https" if self.__original_server_conn.tls_established else "http"

        request_reply = self.channel.ask("request", flow)
        if request_reply == Kill:
            raise Kill()
        if isinstance(request_reply, HTTPResponse):
            flow.response = request_reply
            return

    def establish_server_connection(self, flow):
        address = tcp.Address((flow.request.host, flow.request.port))
        tls = (flow.request.scheme == "https")

        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if address != self.server_conn.address or tls != self.server_conn.tls_established:
                self.set_server(address, tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                self.connect()
        else:
            if not self.server_conn:
                self.connect()
            if tls:
                raise HttpProtocolException("Cannot change scheme in upstream proxy mode.")
            """
            # This is a very ugly (untested) workaround to solve a very ugly problem.
            if self.server_conn and self.server_conn.tls_established and not ssl:
                self.disconnect()
                self.connect()
            elif ssl and not hasattr(self, "connected_to") or self.connected_to != address:
                if self.server_conn.tls_established:
                    self.disconnect()
                    self.connect()

                self.send_request(make_connect_request(address))
                tls_layer = TlsLayer(self, False, True)
                tls_layer._establish_tls_with_server()
            """

    def validate_request(self, request):
        if request.form_in == "absolute" and request.scheme != "http":
            raise HttpException("Invalid request scheme: %s" % request.scheme)

        expected_request_forms = {
            "regular": ("authority", "absolute",),
            "upstream": ("authority", "absolute"),
            "transparent": ("relative",)
        }

        allowed_request_forms = expected_request_forms[self.mode]
        if request.form_in not in allowed_request_forms:
            err_message = "Invalid HTTP request form (expected: %s, got: %s)" % (
                " or ".join(allowed_request_forms), request.form_in
            )
            raise HttpException(err_message)

        if self.mode == "regular" and request.form_in == "absolute":
            request.form_out = "relative"

    def authenticate(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                self.send_response(make_error_response(
                    407,
                    "Proxy Authentication Required",
                    Headers(**self.config.authenticator.auth_challenge_headers())
                ))
                return False
        return True
