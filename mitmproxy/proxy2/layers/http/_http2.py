import time

import h2.connection
import h2.config
import h2.events
import h2.exceptions
import h2.settings

from mitmproxy import http
from mitmproxy.net import http as net_http
from mitmproxy.net.http import http2
from . import RequestEndOfMessage, RequestHeaders, ResponseData, ResponseEndOfMessage, ResponseHeaders
from ._base import HttpConnection, HttpEvent, ReceiveHttp
from ._http_h2 import BufferedH2Connection, H2ConnectionLogger
from ...commands import SendData
from ...context import Context
from ...events import DataReceived, Event, Start
from ...layer import CommandGenerator

h2_events_we_dont_care_about = (
    h2.events.RemoteSettingsChanged,
    h2.events.SettingsAcknowledged
)


class Http2Server(HttpConnection):
    def __init__(self, context: Context):
        super().__init__(context, context.client)

        # noinspection PyTypeChecker
        self.h2_conf = h2.config.H2Configuration(
            client_side=False,
            header_encoding=False,
            validate_outbound_headers=False,
            validate_inbound_headers=False,
            logger=H2ConnectionLogger("server")  # type: ignore
        )
        self.h2_conn = BufferedH2Connection(self.h2_conf)

    def _handle_event(self, event: Event) -> CommandGenerator[None]:
        if isinstance(event, Start):
            self.h2_conn.initiate_connection()
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, HttpEvent):
            if isinstance(event, ResponseHeaders):
                headers = event.response.headers.copy()
                headers.insert(0, ":status", str(event.response.status_code))
                self.h2_conn.send_headers(
                    event.stream_id,
                    headers.fields,
                )
            elif isinstance(event, ResponseData):
                self.h2_conn.send_data(event.stream_id, event.data)
            elif isinstance(event, ResponseEndOfMessage):
                self.h2_conn.send_data(event.stream_id, b"", end_stream=True)
            else:
                raise NotImplementedError(f"Unknown HTTP event: {event}")
            yield SendData(self.conn, self.h2_conn.data_to_send())

        elif isinstance(event, DataReceived):
            try:
                events = self.h2_conn.receive_data(event.data)
            except h2.exceptions.ProtocolError as e:
                events = [e]

            for h2_event in events:
                if isinstance(h2_event, h2_events_we_dont_care_about):
                    pass
                elif isinstance(h2_event, h2.events.RequestReceived):
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
                        b"HTTP/1.1",
                        headers,
                        None,
                        timestamp_start=time.time(),
                    )
                    yield ReceiveHttp(RequestHeaders(h2_event.stream_id, request))
                elif isinstance(h2_event, h2.events.StreamEnded):
                    yield ReceiveHttp(RequestEndOfMessage(h2_event.stream_id))
                else:
                    raise NotImplementedError(f"Unknown event: {h2_event!r}")

            yield SendData(self.conn, self.h2_conn.data_to_send())


class Http2Client:
    pass  # TODO


__all__ = [
    "Http2Client",
    "Http2Server",
]
