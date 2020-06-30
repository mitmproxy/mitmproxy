from typing import ClassVar, Dict, Iterable, List, Optional, Tuple, Type, Union

import h2.connection
import h2.config
import h2.events
import h2.exceptions
import h2.settings
import h2.errors
import h2.utilities
from hyperframe.frame import SettingsFrame

from mitmproxy import http
from mitmproxy.net import http as net_http
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
        logger=H2ConnectionLogger("server")
    )
    h2_conn: BufferedH2Connection

    ReceiveProtocolError: Type[Union[RequestProtocolError, ResponseProtocolError]]
    SendProtocolError: Type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveData: Type[Union[RequestData, ResponseData]]
    SendData: Type[Union[RequestData, ResponseData]]
    ReceiveEndOfMessage: Type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    SendEndOfMessage: Type[Union[RequestEndOfMessage, ResponseEndOfMessage]]

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        self.h2_conn = BufferedH2Connection(self.h2_conf)

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
                raise NotImplementedError(f"Unknown HTTP event: {event}")
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
            raise NotImplementedError(f"Unexpected event: {event!r}")

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        """returns true if further processing should be stopped."""
        if isinstance(event, h2.events.DataReceived):
            # noinspection PyArgumentList
            yield ReceiveHttp(self.ReceiveData(event.stream_id, event.data))
            self.h2_conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
        elif isinstance(event, h2.events.StreamEnded):
            # noinspection PyArgumentList
            yield ReceiveHttp(self.ReceiveEndOfMessage(event.stream_id))
        elif isinstance(event, h2.exceptions.ProtocolError):
            yield from self._unexpected_close(f"HTTP/2 protocol error: {event}")
            return True
        elif isinstance(event, h2.events.ConnectionTerminated):
            yield from self._unexpected_close(f"HTTP/2 connection closed: {event!r}")
            return True
        elif isinstance(event, h2.events.StreamReset):
            # noinspection PyArgumentList
            yield ReceiveHttp(self.ReceiveProtocolError(event.stream_id, "Stream reset"))
        elif isinstance(event, h2.events.RemoteSettingsChanged):
            pass
        elif isinstance(event, h2.events.SettingsAcknowledged):
            pass
        else:
            raise NotImplementedError(f"Unknown event: {event!r}")

    def _unexpected_close(self, err: str) -> CommandGenerator[None]:
        yield CloseConnection(self.conn)
        for stream_id, stream in self.h2_conn.streams.items():
            if stream.open:
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
        client_side=False,
        **Http2Connection.h2_conf_defaults
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
            if event.response.http_version != b"HTTP/2":
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
            method, scheme, host, port, path, headers = parse_h2_request_headers(event.headers)
            request = http.HTTPRequest(
                "relative",
                method,
                scheme,
                host,
                port,
                path,
                b"HTTP/2",
                headers,
                None,
            )
            yield ReceiveHttp(RequestHeaders(event.stream_id, request))
        else:
            return (yield from super().handle_h2_event(event))


class Http2Client(Http2Connection):
    h2_conf = h2.config.H2Configuration(
        client_side=True,
        **Http2Connection.h2_conf_defaults
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
        self.h2_conn.update_settings({SettingsFrame.ENABLE_PUSH: 0})

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, RequestHeaders):
            headers = [
                (b':method', event.request.method),
                (b':scheme', event.request.scheme),
                (b':path', event.request.path),
                *event.request.headers.fields
            ]
            if event.request.http_version == b"HTTP/2":
                """
                From the h2 spec:

                To ensure that the HTTP/1.1 request line can be reproduced accurately, this pseudo-header field MUST be 
                omitted when translating from an HTTP/1.1 request that has a request target in origin or asterisk form 
                (see [RFC7230], Section 5.3). Clients that generate HTTP/2 requests directly SHOULD use the :authority 
                pseudo-header field instead of the Host header field. An intermediary that converts an HTTP/2 request to 
                HTTP/1.1 MUST create a Host header field if one is not present in a request by copying the value of the 
                :authority pseudo-header field.
                """
                if headers[3][0].lower() == b"host":
                    headers[3] = (b":authority", headers[3][1])
            else:
                headers = normalize_h1_headers(headers, True)




            self.h2_conn.send_headers(
                event.stream_id,
                headers,
            )
            yield SendData(self.conn, self.h2_conn.data_to_send())
        else:
            yield from super()._handle_event(event)

    def handle_h2_event(self, event: h2.events.Event) -> CommandGenerator[bool]:
        if isinstance(event, h2.events.ResponseReceived):
            headers = net_http.Headers([(k, v) for k, v in event.headers])
            status_code = headers.pop(":status")
            response = http.HTTPResponse(
                b"HTTP/2",
                status_code,
                b"",
                headers,
                None,
            )
            yield ReceiveHttp(ResponseHeaders(event.stream_id, response))
        else:
            return (yield from super().handle_h2_event(event))


def parse_h2_request_headers(
        h2_headers: Iterable[Tuple[bytes, bytes]]
) -> Tuple[bytes, bytes, Optional[bytes], Optional[int], bytes, net_http.Headers]:
    """Split HTTP/2 pseudo-headers from the actual headers and parse them."""
    pseudo_headers: Dict[bytes, bytes] = {}
    i = 0
    for i, (header, value) in enumerate(h2_headers):
        if header.startswith(b":"):
            if header in pseudo_headers:
                raise ValueError(f"Duplicate HTTP/2 pseudo headers: {header}")
            pseudo_headers[header] = value
        else:
            # Pseudo-headers must be at the start, we are done here.
            break

    headers = net_http.Headers(h2_headers[i:])

    try:
        method: bytes = pseudo_headers.pop(b":method")
        scheme: bytes = pseudo_headers.pop(b":scheme")  # this raises for HTTP/2 CONNECT requests
        path: bytes = pseudo_headers.pop(b":path")
        authority: bytes = pseudo_headers.pop(b":authority", None)
    except KeyError as e:
        raise ValueError(f"Required pseudo header is missing: {e}")

    if pseudo_headers:
        raise ValueError(f"Unknown pseudo headers: {pseudo_headers}")

    host = None
    port = None
    if authority is not None:
        headers.insert(0, b"Host", authority)
        host, _, portstr = authority.rpartition(b":")  # partition from the right to support IPv6 addresses
        if host == b"":
            host = portstr
            port = 443 if scheme == b'https' else 80
        else:
            port = int(portstr)

    return method, scheme, host, port, path, headers


__all__ = [
    "Http2Client",
    "Http2Server",
]
