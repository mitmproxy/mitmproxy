import time
from typing import ClassVar, Dict, Iterable, List, Optional, Set, Tuple, Type, Union

import h2.connection
import h2.config
import h2.events
import h2.exceptions
import h2.settings
import h2.errors
import h2.utilities

from mitmproxy import http
from mitmproxy.net import http as net_http
from mitmproxy.net.http import url
from mitmproxy.utils import human
from . import RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, ResponseData, \
    ResponseEndOfMessage, ResponseHeaders, ResponseProtocolError
from ._base import HttpConnection, HttpEvent, ReceiveHttp
from ._http_h2 import BufferedH2Connection, H2ConnectionLogger
from ...commands import CloseConnection, Log, SendData
from ...context import Connection, Context
from ...events import ConnectionClosed, DataReceived, Event, Start
from ...layer import CommandGenerator


class Http2Connection(HttpConnection):
    h2_conf: ClassVar[h2.config.H2Configuration]
    h2_conf_defaults = dict(
        header_encoding=False,
        validate_outbound_headers=False,
        validate_inbound_headers=False,
        normalize_inbound_headers=False,
        normalize_outbound_headers=False,
        # logger=H2ConnectionLogger("server")
    )
    h2_conn: BufferedH2Connection
    active_stream_ids: Set[int]
    """keep track of all active stream ids to send protocol errors on teardown"""

    ReceiveProtocolError: Type[Union[RequestProtocolError, ResponseProtocolError]]
    SendProtocolError: Type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveData: Type[Union[RequestData, ResponseData]]
    SendData: Type[Union[RequestData, ResponseData]]
    ReceiveEndOfMessage: Type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    SendEndOfMessage: Type[Union[RequestEndOfMessage, ResponseEndOfMessage]]

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        self.h2_conn = BufferedH2Connection(self.h2_conf)
        self.active_stream_ids = set()

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, Start):
            self.h2_conn.initiate_connection()
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, HttpEvent):
            if isinstance(event, self.SendData):
                self.h2_conn.send_data(event.stream_id, event.data)
            elif isinstance(event, self.SendEndOfMessage):
                self.h2_conn.send_data(event.stream_id, b"", end_stream=True)
            elif isinstance(event, self.SendProtocolError):
                self.h2_conn.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
            else:
                raise AssertionError(f"Unexpected event: {event}")
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, DataReceived):
            try:
                events = self.h2_conn.receive_data(event.data)
            except h2.exceptions.ProtocolError as e:
                events = [e]

            for h2_event in events:
                if (yield from self.handle_h2_event(h2_event)):
                    return

            data_to_send = self.h2_conn.data_to_send()
            if data_to_send:
                yield SendData(self.conn, data_to_send)

        elif isinstance(event, ConnectionClosed):
            yield from self._unexpected_close("peer closed connection")
        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        """returns true if further processing should be stopped."""
        if isinstance(event, h2.events.DataReceived):
            if event.stream_id in self.active_stream_ids:
                # noinspection PyArgumentList
                yield ReceiveHttp(self.ReceiveData(event.stream_id, event.data))
            self.h2_conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
        elif isinstance(event, h2.events.StreamEnded):
            if event.stream_id in self.active_stream_ids:
                # noinspection PyArgumentList
                yield ReceiveHttp(self.ReceiveEndOfMessage(event.stream_id))
                self.active_stream_ids.remove(event.stream_id)
        elif isinstance(event, h2.exceptions.ProtocolError):
            yield from self._unexpected_close(f"HTTP/2 protocol error: {event}")
            return True
        elif isinstance(event, h2.events.ConnectionTerminated):
            yield from self._unexpected_close(f"HTTP/2 connection closed: {event!r}")
            return True
        elif isinstance(event, h2.events.StreamReset):
            if event.stream_id in self.active_stream_ids:
                # noinspection PyArgumentList
                yield ReceiveHttp(self.ReceiveProtocolError(event.stream_id, "Stream reset"))
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            pass
        elif isinstance(event, h2.events.SettingsAcknowledged):
            pass
        elif isinstance(event, h2.events.PriorityUpdated):
            pass
        elif isinstance(event, h2.events.UnknownFrameReceived):
            # https://http2.github.io/http2-spec/#rfc.section.4.1
            # Implementations MUST ignore and discard any frame that has a type that is unknown.
            yield Log(f"Ignoring unknown HTTP/2 frame type: {event.frame.type}")
        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def _unexpected_close(self, err: str) -> CommandGenerator[None]:
        yield CloseConnection(self.conn)
        for stream_id in self.active_stream_ids:
            # noinspection PyArgumentList
            yield ReceiveHttp(self.ReceiveProtocolError(stream_id, err))


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
    SendProtocolError = ResponseProtocolError
    ReceiveData = RequestData
    SendData = ResponseData
    ReceiveEndOfMessage = RequestEndOfMessage
    SendEndOfMessage = ResponseEndOfMessage

    def __init__(self, context: Context):
        super().__init__(context, context.client)

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, ResponseHeaders):
            headers = [
                (b":status", b"%d" % event.response.status_code),
                *event.response.headers.fields
            ]
            if not event.response.is_http2:
                headers = normalize_h1_headers(headers, False)

            self.h2_conn.send_headers(
                event.stream_id,
                headers,
            )
            yield SendData(self.conn, self.h2_conn.data_to_send())
        else:
            yield from super()._handle_event(event)

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        if isinstance(event, h2.events.RequestReceived):
            try:
                host, port, method, scheme, authority, path, headers = parse_h2_request_headers(event.headers)
            except ValueError as e:
                yield Log(f"{human.format_address(self.conn.peername)}: {e}")
                self.h2_conn.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
                yield SendData(self.conn, self.h2_conn.data_to_send())
                return
            request = http.HTTPRequest(
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
            self.active_stream_ids.add(event.stream_id)
            yield ReceiveHttp(RequestHeaders(event.stream_id, request))
        else:
            return (yield from super().handle_h2_event(event))


class Http2Client(Http2Connection):
    h2_conf = h2.config.H2Configuration(
        **Http2Connection.h2_conf_defaults,
        client_side = True,
    )

    ReceiveProtocolError = ResponseProtocolError
    SendProtocolError = RequestProtocolError
    ReceiveData = ResponseData
    SendData = RequestData
    ReceiveEndOfMessage = ResponseEndOfMessage
    SendEndOfMessage = RequestEndOfMessage

    def __init__(self, context: Context):
        super().__init__(context, context.server)
        # Disable HTTP/2 push for now to keep things simple.
        # don't send here, that is done as part of initiate_connection().
        self.h2_conn.local_settings.enable_push = False

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, RequestHeaders):
            pseudo_headers = [
                (b':method', event.request.method),
                (b':scheme', event.request.scheme),
                (b':path', event.request.path),
            ]
            if event.request.authority:
                pseudo_headers.append((b":authority", event.request.data.authority))
            headers = pseudo_headers + list(event.request.headers.fields)
            if not event.request.is_http2:
                headers = normalize_h1_headers(headers, True)

            self.h2_conn.send_headers(
                event.stream_id,
                headers,
            )
            self.active_stream_ids.add(event.stream_id)
            yield SendData(self.conn, self.h2_conn.data_to_send())
        else:
            yield from super()._handle_event(event)

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        if isinstance(event, h2.events.ResponseReceived):
            status_code, headers = parse_h2_response_headers(event.headers)
            response = http.HTTPResponse(
                http_version=b"HTTP/2.0",
                status_code=status_code,
                reason=b"",
                headers=headers,
                content=None,
                trailers=None,
                timestamp_start=time.time(),
                timestamp_end=None,
            )
            yield ReceiveHttp(ResponseHeaders(event.stream_id, response))
        else:
            return (yield from super().handle_h2_event(event))


def split_pseudo_headers(h2_headers: Iterable[Tuple[bytes, bytes]]) -> Tuple[Dict[bytes, bytes], net_http.Headers]:
    pseudo_headers: Dict[bytes, bytes] = {}
    i = 0
    for (header, value) in h2_headers:
        if header.startswith(b":"):
            if header in pseudo_headers:
                raise ValueError(f"Duplicate HTTP/2 pseudo header: {header}")
            pseudo_headers[header] = value
            i += 1
        else:
            # Pseudo-headers must be at the start, we are done here.
            break

    headers = net_http.Headers(h2_headers[i:])

    return pseudo_headers, headers

def parse_h2_request_headers(
        h2_headers: Iterable[Tuple[bytes, bytes]]
) -> Tuple[str, int, bytes, bytes, bytes, bytes, net_http.Headers]:
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


def parse_h2_response_headers(h2_headers: Iterable[Tuple[bytes, bytes]]) -> Tuple[int, net_http.Headers]:
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
