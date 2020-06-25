import time
from typing import ClassVar

import h2.connection
import h2.config
import h2.events
import h2.exceptions
import h2.settings
import h2.errors
import h2.utilities

from mitmproxy import http
from mitmproxy.net import http as net_http
from mitmproxy.net.http import http2
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
    h2_conn: BufferedH2Connection

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        self.h2_conn = BufferedH2Connection(self.h2_conf)


class Http2Server(Http2Connection):
    # noinspection PyTypeChecker
    h2_conf = h2.config.H2Configuration(
        client_side=False,
        header_encoding=False,
        validate_outbound_headers=False,
        validate_inbound_headers=False,
        normalize_inbound_headers=False,
        normalize_outbound_headers=False,
        logger=H2ConnectionLogger("server")  # type: ignore
    )

    def __init__(self, context: Context):
        super().__init__(context, context.client)

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, Start):
            self.h2_conn.initiate_connection()
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, HttpEvent):
            if isinstance(event, ResponseHeaders):
                headers = (
                    (b":status", b"%d" % event.response.status_code),
                    *event.response.headers.fields
                )
                if event.response.data.http_version != b"HTTP/2":
                    # HTTP/1 servers commonly send capitalized headers (Content-Length vs content-length),
                    # which isn't valid HTTP/2. As such we normalize.
                    headers = h2.utilities.normalize_outbound_headers(
                        headers,
                        h2.utilities.HeaderValidationFlags(False, False, True, False)
                    )
                    # make sure that this is not just an iterator but an iterable,
                    # otherwise hyper-h2 will silently drop headers.
                    headers = list(headers)
                self.h2_conn.send_headers(
                    event.stream_id,
                    headers,
                )
            elif isinstance(event, ResponseData):
                self.h2_conn.send_data(event.stream_id, event.data)
            elif isinstance(event, ResponseEndOfMessage):
                self.h2_conn.send_data(event.stream_id, b"", end_stream=True)
            elif isinstance(event, ResponseProtocolError):
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
                if isinstance(h2_event, h2.events.RequestReceived):
                    headers = net_http.Headers([(k, v) for k, v in h2_event.headers])
                    first_line_format, method, scheme, host, port, path = http2.parse_headers(headers)
                    headers["Host"] = headers.pop(":authority")  # FIXME: temporary workaround
                    request = http.HTTPRequest(
                        first_line_format,
                        method,
                        scheme,
                        host,
                        port,
                        path,
                        b"HTTP/1.1",  # FIXME: Figure out how to smooth h2 <-> h1.
                        headers,
                        None,
                        timestamp_start=time.time(),
                    )
                    yield ReceiveHttp(RequestHeaders(h2_event.stream_id, request))
                elif isinstance(h2_event, h2.events.DataReceived):
                    yield ReceiveHttp(RequestData(h2_event.stream_id, h2_event.data))
                    self.h2_conn.acknowledge_received_data(len(h2_event.data), h2_event.stream_id)
                elif isinstance(h2_event, h2.events.StreamEnded):
                    yield ReceiveHttp(RequestEndOfMessage(h2_event.stream_id))
                elif isinstance(h2_event, h2.exceptions.ProtocolError):
                    yield CloseConnection(self.conn)
                    yield from self._notify_close(f"HTTP/2 protocol error: {h2_event}")
                    return
                elif isinstance(h2_event, h2.events.ConnectionTerminated):
                    yield CloseConnection(self.conn)
                    yield from self._notify_close(f"HTTP/2 connection closed: {h2_event!r}")
                    return
                elif isinstance(h2_event, h2.events.StreamReset):
                    yield ReceiveHttp(RequestProtocolError(h2_event.stream_id, "EOF"))
                elif isinstance(h2_event, h2.events.RemoteSettingsChanged):
                    pass
                elif isinstance(h2_event, h2.events.SettingsAcknowledged):
                    pass
                else:
                    raise NotImplementedError(f"Unknown event: {h2_event!r}")

            data_to_send = self.h2_conn.data_to_send()
            if data_to_send:
                yield SendData(self.conn, data_to_send)
        elif isinstance(event, ConnectionClosed):
            yield CloseConnection(self.conn)
            yield from self._notify_close("peer closed connection")
        else:
            raise NotImplementedError(f"Unexpected event: {event!r}")

    def _notify_close(self, err: str) -> CommandGenerator[None]:
        for stream_id, stream in self.h2_conn.streams.items():
            if stream.open:
                yield ReceiveHttp(RequestProtocolError(stream_id, err))


class Http2Client:
    pass  # TODO


__all__ = [
    "Http2Client",
    "Http2Server",
]
