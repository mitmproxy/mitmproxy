import collections
import time
from enum import Enum
from typing import ClassVar, DefaultDict, Dict, List, Optional, Sequence, Tuple, Type, Union

import h2.config
import h2.connection
import h2.errors
import h2.events
import h2.exceptions
import h2.settings
import h2.stream
import h2.utilities

from mitmproxy import http, version
from mitmproxy.connection import Connection
from mitmproxy.net.http import status_codes, url
from mitmproxy.utils import human
from . import RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, ResponseData, \
    ResponseEndOfMessage, ResponseHeaders, RequestTrailers, ResponseTrailers, ResponseProtocolError
from ._base import HttpConnection, HttpEvent, ReceiveHttp, format_error
from ._http_h2 import BufferedH2Connection, H2ConnectionLogger
from ...commands import CloseConnection, Log, SendData
from ...context import Context
from ...events import ConnectionClosed, DataReceived, Event, Start
from ...layer import CommandGenerator
from ...utils import expect


class StreamState(Enum):
    EXPECTING_HEADERS = 1
    HEADERS_RECEIVED = 2


class Http2Connection(HttpConnection):
    h2_conf: ClassVar[h2.config.H2Configuration]
    h2_conf_defaults = dict(
        header_encoding=False,
        validate_outbound_headers=False,
        validate_inbound_headers=True,
        normalize_inbound_headers=False,  # changing this to True is required to pass h2spec
        normalize_outbound_headers=False,
    )
    h2_conn: BufferedH2Connection
    streams: Dict[int, StreamState]
    """keep track of all active stream ids to send protocol errors on teardown"""

    ReceiveProtocolError: Type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveData: Type[Union[RequestData, ResponseData]]
    ReceiveTrailers: Type[Union[RequestTrailers, ResponseTrailers]]
    ReceiveEndOfMessage: Type[Union[RequestEndOfMessage, ResponseEndOfMessage]]

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        if self.debug:
            self.h2_conf.logger = H2ConnectionLogger(f"{human.format_address(self.context.client.peername)}: "
                                                     f"{self.__class__.__name__}")
        self.h2_conn = BufferedH2Connection(self.h2_conf)
        self.streams = {}

    def is_closed(self, stream_id: int) -> bool:
        """Check if a non-idle stream is closed"""
        stream = self.h2_conn.streams.get(stream_id, None)
        if (
            stream is not None
            and
            stream.state_machine.state is not h2.stream.StreamState.CLOSED
            and
            self.h2_conn.state_machine.state is not h2.connection.ConnectionState.CLOSED
        ):
            return False
        else:
            return True

    def is_open_for_us(self, stream_id: int) -> bool:
        """Check if we can write to a non-idle stream."""
        stream = self.h2_conn.streams.get(stream_id, None)
        if (
            stream is not None
            and
            stream.state_machine.state is not h2.stream.StreamState.HALF_CLOSED_LOCAL
            and
            stream.state_machine.state is not h2.stream.StreamState.CLOSED
            and
            self.h2_conn.state_machine.state is not h2.connection.ConnectionState.CLOSED
        ):
            return True
        else:
            return False

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, Start):
            self.h2_conn.initiate_connection()
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, HttpEvent):
            if isinstance(event, (RequestData, ResponseData)):
                if self.is_open_for_us(event.stream_id):
                    self.h2_conn.send_data(event.stream_id, event.data)
            elif isinstance(event, (RequestTrailers, ResponseTrailers)):
                if self.is_open_for_us(event.stream_id):
                    trailers = [*event.trailers.fields]
                    self.h2_conn.send_headers(event.stream_id, trailers, end_stream=True)
            elif isinstance(event, (RequestEndOfMessage, ResponseEndOfMessage)):
                if self.is_open_for_us(event.stream_id):
                    self.h2_conn.end_stream(event.stream_id)
            elif isinstance(event, (RequestProtocolError, ResponseProtocolError)):
                if not self.is_closed(event.stream_id):
                    code = {
                        status_codes.CLIENT_CLOSED_REQUEST: h2.errors.ErrorCodes.CANCEL,
                    }.get(event.code, h2.errors.ErrorCodes.INTERNAL_ERROR)
                    stream: h2.stream.H2Stream = self.h2_conn.streams[event.stream_id]
                    send_error_message = (
                        isinstance(event, ResponseProtocolError)
                        and self.is_open_for_us(event.stream_id)
                        and not stream.state_machine.headers_sent
                        and event.code != status_codes.NO_RESPONSE
                    )
                    if send_error_message:
                        self.h2_conn.send_headers(event.stream_id, [
                            (b":status", b"%d" % event.code),
                            (b"server", version.MITMPROXY.encode()),
                            (b"content-type", b"text/html"),
                        ])
                        self.h2_conn.send_data(
                            event.stream_id,
                            format_error(event.code, event.message),
                            end_stream=True
                        )
                    else:
                        self.h2_conn.reset_stream(event.stream_id, code)
            else:
                raise AssertionError(f"Unexpected event: {event}")
            data_to_send = self.h2_conn.data_to_send()
            if data_to_send:
                yield SendData(self.conn, data_to_send)

        elif isinstance(event, DataReceived):
            try:
                try:
                    events = self.h2_conn.receive_data(event.data)
                except ValueError as e:  # pragma: no cover
                    # this should never raise a ValueError, but we triggered one while fuzzing:
                    # https://github.com/python-hyper/hyper-h2/issues/1231
                    # this stays here as defense-in-depth.
                    raise h2.exceptions.ProtocolError(f"uncaught hyper-h2 error: {e}") from e
            except h2.exceptions.ProtocolError as e:
                events = [e]

            for h2_event in events:
                if self.debug:
                    yield Log(f"{self.debug}[h2] {h2_event}", "debug")
                if (yield from self.handle_h2_event(h2_event)):
                    if self.debug:
                        yield Log(f"{self.debug}[h2] done", "debug")
                    return

            data_to_send = self.h2_conn.data_to_send()
            if data_to_send:
                yield SendData(self.conn, data_to_send)

        elif isinstance(event, ConnectionClosed):
            yield from self.close_connection("peer closed connection")
        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        """returns true if further processing should be stopped."""
        if isinstance(event, h2.events.DataReceived):
            state = self.streams.get(event.stream_id, None)
            if state is StreamState.HEADERS_RECEIVED:
                yield ReceiveHttp(self.ReceiveData(event.stream_id, event.data))
            elif state is StreamState.EXPECTING_HEADERS:
                yield from self.protocol_error(f"Received HTTP/2 data frame, expected headers.")
                return True
            self.h2_conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
        elif isinstance(event, h2.events.TrailersReceived):
            trailers = http.Headers(event.headers)
            yield ReceiveHttp(self.ReceiveTrailers(event.stream_id, trailers))
        elif isinstance(event, h2.events.StreamEnded):
            state = self.streams.get(event.stream_id, None)
            if state is StreamState.HEADERS_RECEIVED:
                yield ReceiveHttp(self.ReceiveEndOfMessage(event.stream_id))
            elif state is StreamState.EXPECTING_HEADERS:
                raise AssertionError("unreachable")
            if self.is_closed(event.stream_id):
                self.streams.pop(event.stream_id, None)
        elif isinstance(event, h2.events.StreamReset):
            if event.stream_id in self.streams:
                try:
                    err_str = h2.errors.ErrorCodes(event.error_code).name
                except ValueError:
                    err_str = str(event.error_code)
                err_code = {
                    h2.errors.ErrorCodes.CANCEL: status_codes.CLIENT_CLOSED_REQUEST,
                }.get(event.error_code, self.ReceiveProtocolError.code)
                yield ReceiveHttp(self.ReceiveProtocolError(event.stream_id, f"stream reset by client ({err_str})",
                                                            code=err_code))
                self.streams.pop(event.stream_id)
            else:
                pass  # We don't track priority frames which could be followed by a stream reset here.
        elif isinstance(event, h2.exceptions.ProtocolError):
            yield from self.protocol_error(f"HTTP/2 protocol error: {event}")
            return True
        elif isinstance(event, h2.events.ConnectionTerminated):
            yield from self.close_connection(f"HTTP/2 connection closed: {event!r}")
            return True
            # The implementation above isn't really ideal, we should probably only terminate streams > last_stream_id?
            # We currently lack a mechanism to signal that connections are still active but cannot be reused.
            # for stream_id in self.streams:
            #    if stream_id > event.last_stream_id:
            #        yield ReceiveHttp(self.ReceiveProtocolError(stream_id, f"HTTP/2 connection closed: {event!r}"))
            #        self.streams.pop(stream_id)
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            pass
        elif isinstance(event, h2.events.SettingsAcknowledged):
            pass
        elif isinstance(event, h2.events.PriorityUpdated):
            pass
        elif isinstance(event, h2.events.PingReceived):
            pass
        elif isinstance(event, h2.events.PingAckReceived):
            pass
        elif isinstance(event, h2.events.PushedStreamReceived):
            yield Log("Received HTTP/2 push promise, even though we signalled no support.", "error")
        elif isinstance(event, h2.events.UnknownFrameReceived):
            # https://http2.github.io/http2-spec/#rfc.section.4.1
            # Implementations MUST ignore and discard any frame that has a type that is unknown.
            yield Log(f"Ignoring unknown HTTP/2 frame type: {event.frame.type}")
        else:
            raise AssertionError(f"Unexpected event: {event!r}")
        return False

    def protocol_error(
        self,
        message: str,
        error_code: int = h2.errors.ErrorCodes.PROTOCOL_ERROR,
    ) -> CommandGenerator[None]:
        yield Log(f"{human.format_address(self.conn.peername)}: {message}")
        self.h2_conn.close_connection(error_code, message.encode())
        yield SendData(self.conn, self.h2_conn.data_to_send())
        yield from self.close_connection(message)

    def close_connection(self, msg: str) -> CommandGenerator[None]:
        yield CloseConnection(self.conn)
        for stream_id in self.streams:
            yield ReceiveHttp(self.ReceiveProtocolError(stream_id, msg))
        self.streams.clear()
        self._handle_event = self.done  # type: ignore

    @expect(DataReceived, HttpEvent, ConnectionClosed)
    def done(self, _) -> CommandGenerator[None]:
        yield from ()


def normalize_h1_headers(headers: List[Tuple[bytes, bytes]], is_client: bool) -> List[Tuple[bytes, bytes]]:
    # HTTP/1 servers commonly send capitalized headers (Content-Length vs content-length),
    # which isn't valid HTTP/2. As such we normalize.
    headers = h2.utilities.normalize_outbound_headers(
        headers,
        h2.utilities.HeaderValidationFlags(is_client, False, not is_client, False)
    )
    # make sure that this is not just an iterator but an iterable,
    # otherwise hyper-h2 will silently drop headers.
    headers = list(headers)
    return headers


class Http2Server(Http2Connection):
    h2_conf = h2.config.H2Configuration(
        **Http2Connection.h2_conf_defaults,
        client_side=False,
    )

    ReceiveProtocolError = RequestProtocolError
    ReceiveData = RequestData
    ReceiveTrailers = RequestTrailers
    ReceiveEndOfMessage = RequestEndOfMessage

    def __init__(self, context: Context):
        super().__init__(context, context.client)

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, ResponseHeaders):
            if self.is_open_for_us(event.stream_id):
                headers = [
                    (b":status", b"%d" % event.response.status_code),
                    *event.response.headers.fields
                ]
                if not event.response.is_http2:
                    headers = normalize_h1_headers(headers, False)

                self.h2_conn.send_headers(
                    event.stream_id,
                    headers,
                    end_stream=event.end_stream,
                )
                yield SendData(self.conn, self.h2_conn.data_to_send())
        else:
            yield from super()._handle_event(event)

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        if isinstance(event, h2.events.RequestReceived):
            try:
                host, port, method, scheme, authority, path, headers = parse_h2_request_headers(event.headers)
            except ValueError as e:
                yield from self.protocol_error(f"Invalid HTTP/2 request headers: {e}")
                return True
            request = http.Request(
                host=host,
                port=port,
                method=method,
                scheme=scheme,
                authority=authority,
                path=path,
                http_version=b"HTTP/2.0",
                headers=headers,
                content=None,
                trailers=None,
                timestamp_start=time.time(),
                timestamp_end=None,
            )
            self.streams[event.stream_id] = StreamState.HEADERS_RECEIVED
            yield ReceiveHttp(RequestHeaders(event.stream_id, request, end_stream=bool(event.stream_ended)))
            return False
        else:
            return (yield from super().handle_h2_event(event))


class Http2Client(Http2Connection):
    h2_conf = h2.config.H2Configuration(
        **Http2Connection.h2_conf_defaults,
        client_side=True,
    )

    ReceiveProtocolError = ResponseProtocolError
    ReceiveData = ResponseData
    ReceiveTrailers = ResponseTrailers
    ReceiveEndOfMessage = ResponseEndOfMessage

    our_stream_id: Dict[int, int]
    their_stream_id: Dict[int, int]
    stream_queue: DefaultDict[int, List[Event]]
    """Queue of streams that we haven't sent yet because we have reached MAX_CONCURRENT_STREAMS"""
    provisional_max_concurrency: Optional[int] = 10
    """A provisional currency limit before we get the server's first settings frame."""

    def __init__(self, context: Context):
        super().__init__(context, context.server)
        # Disable HTTP/2 push for now to keep things simple.
        # don't send here, that is done as part of initiate_connection().
        self.h2_conn.local_settings.enable_push = 0
        # hyper-h2 pitfall: we need to acknowledge here, otherwise its sends out the old settings.
        self.h2_conn.local_settings.acknowledge()
        self.our_stream_id = {}
        self.their_stream_id = {}
        self.stream_queue = collections.defaultdict(list)

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        # We can't reuse stream ids from the client because they may arrived reordered here
        # and HTTP/2 forbids opening a stream on a lower id than what was previously sent (see test_stream_concurrency).
        # To mitigate this, we transparently map the outside's stream id to our stream id.
        if isinstance(event, HttpEvent):
            ours = self.our_stream_id.get(event.stream_id, None)
            if ours is None:
                no_free_streams = (
                    self.h2_conn.open_outbound_streams >=
                    (self.provisional_max_concurrency or self.h2_conn.remote_settings.max_concurrent_streams)
                )
                if no_free_streams:
                    self.stream_queue[event.stream_id].append(event)
                    return
                ours = self.h2_conn.get_next_available_stream_id()
                self.our_stream_id[event.stream_id] = ours
                self.their_stream_id[ours] = event.stream_id
            event.stream_id = ours

        for cmd in self._handle_event2(event):
            if isinstance(cmd, ReceiveHttp):
                cmd.event.stream_id = self.their_stream_id[cmd.event.stream_id]
            yield cmd

        can_resume_queue = (
            self.stream_queue and
            self.h2_conn.open_outbound_streams < (
                self.provisional_max_concurrency or self.h2_conn.remote_settings.max_concurrent_streams
            )
        )
        if can_resume_queue:
            # popitem would be LIFO, but we want FIFO.
            events = self.stream_queue.pop(next(iter(self.stream_queue)))
            for event in events:
                yield from self._handle_event(event)

    def _handle_event2(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, RequestHeaders):
            pseudo_headers = [
                (b':method', event.request.data.method),
                (b':scheme', event.request.data.scheme),
                (b':path', event.request.data.path),
            ]
            if event.request.authority:
                pseudo_headers.append((b":authority", event.request.data.authority))

            if event.request.is_http2:
                hdrs = list(event.request.headers.fields)
            else:
                headers = event.request.headers
                if not event.request.authority and "host" in headers:
                    headers = headers.copy()
                    pseudo_headers.append((b":authority", headers.pop(b"host")))
                hdrs = normalize_h1_headers(list(headers.fields), True)

            self.h2_conn.send_headers(
                event.stream_id,
                pseudo_headers + hdrs,
                end_stream=event.end_stream,
            )
            self.streams[event.stream_id] = StreamState.EXPECTING_HEADERS
            yield SendData(self.conn, self.h2_conn.data_to_send())
        else:
            yield from super()._handle_event(event)

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        if isinstance(event, h2.events.ResponseReceived):
            if self.streams.get(event.stream_id, None) is not StreamState.EXPECTING_HEADERS:
                yield from self.protocol_error(f"Received unexpected HTTP/2 response.")
                return True

            try:
                status_code, headers = parse_h2_response_headers(event.headers)
            except ValueError as e:
                yield from self.protocol_error(f"Invalid HTTP/2 response headers: {e}")
                return True

            response = http.Response(
                http_version=b"HTTP/2.0",
                status_code=status_code,
                reason=b"",
                headers=headers,
                content=None,
                trailers=None,
                timestamp_start=time.time(),
                timestamp_end=None,
            )
            self.streams[event.stream_id] = StreamState.HEADERS_RECEIVED
            yield ReceiveHttp(ResponseHeaders(event.stream_id, response, bool(event.stream_ended)))
            return False
        elif isinstance(event, h2.events.RequestReceived):
            yield from self.protocol_error(f"HTTP/2 protocol error: received request from server")
            return True
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            # We have received at least one settings from now,
            # which means we can rely on the max concurrency in remote_settings
            self.provisional_max_concurrency = None
            return (yield from super().handle_h2_event(event))
        else:
            return (yield from super().handle_h2_event(event))


def split_pseudo_headers(h2_headers: Sequence[Tuple[bytes, bytes]]) -> Tuple[Dict[bytes, bytes], http.Headers]:
    pseudo_headers: Dict[bytes, bytes] = {}
    i = 0
    for (header, value) in h2_headers:
        if header.startswith(b":"):
            if header in pseudo_headers:
                raise ValueError(f"Duplicate HTTP/2 pseudo header: {header!r}")
            pseudo_headers[header] = value
            i += 1
        else:
            # Pseudo-headers must be at the start, we are done here.
            break

    headers = http.Headers(h2_headers[i:])

    return pseudo_headers, headers


def parse_h2_request_headers(
    h2_headers: Sequence[Tuple[bytes, bytes]]
) -> Tuple[str, int, bytes, bytes, bytes, bytes, http.Headers]:
    """Split HTTP/2 pseudo-headers from the actual headers and parse them."""
    pseudo_headers, headers = split_pseudo_headers(h2_headers)

    try:
        method: bytes = pseudo_headers.pop(b":method")
        scheme: bytes = pseudo_headers.pop(b":scheme")  # this raises for HTTP/2 CONNECT requests
        path: bytes = pseudo_headers.pop(b":path")
        authority: bytes = pseudo_headers.pop(b":authority", b"")
    except KeyError as e:
        raise ValueError(f"Required pseudo header is missing: {e}")

    if pseudo_headers:
        raise ValueError(f"Unknown pseudo headers: {pseudo_headers}")

    if authority:
        host, port = url.parse_authority(authority, check=True)
        if port is None:
            port = 80 if scheme == b'http' else 443
    else:
        host = ""
        port = 0

    return host, port, method, scheme, authority, path, headers


def parse_h2_response_headers(h2_headers: Sequence[Tuple[bytes, bytes]]) -> Tuple[int, http.Headers]:
    """Split HTTP/2 pseudo-headers from the actual headers and parse them."""
    pseudo_headers, headers = split_pseudo_headers(h2_headers)

    try:
        status_code: int = int(pseudo_headers.pop(b":status"))
    except KeyError as e:
        raise ValueError(f"Required pseudo header is missing: {e}")

    if pseudo_headers:
        raise ValueError(f"Unknown pseudo headers: {pseudo_headers}")

    return status_code, headers


__all__ = [
    "Http2Client",
    "Http2Server",
]
