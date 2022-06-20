from abc import abstractmethod
from typing import Optional, Union

from aioquic.quic.connection import QuicConnection
from aioquic.h3.connection import (
    H3Connection,
    FrameUnexpected,
    ErrorCode as H3ErrorCode,
)
from aioquic.h3 import events as h3_events

from mitmproxy import version
from mitmproxy.net.http import status_codes
from mitmproxy.proxy import context, events, layer
from mitmproxy.proxy.layers.quic import (
    QuicConnectionEvent,
    QuicGetConnection,
    QuicTransmit,
)

from . import (
    RequestData,
    RequestEndOfMessage,
    RequestHeaders,
    RequestProtocolError,
    ResponseData,
    ResponseEndOfMessage,
    ResponseHeaders,
    RequestTrailers,
    ResponseTrailers,
    ResponseProtocolError,
)
from ._base import (
    HttpConnection,
    HttpEvent,
    format_error,
    get_request_headers,
    get_response_headers,
)


class Http3Connection(HttpConnection):
    quic: Optional[QuicConnection] = None
    h3_conn: Optional[H3Connection] = None

    EventData: type[Union[RequestData, ResponseData]]
    ReceiveData: type[Union[RequestData, ResponseData]]
    EventEndOfMessage: type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    ReceiveEndOfMessage: type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    EventHeaders: type[Union[RequestHeaders, ResponseHeaders]]
    ReceiveHeaders: type[Union[RequestHeaders, ResponseHeaders]]
    EventProtocolError: type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveProtocolError: type[Union[RequestProtocolError, ResponseProtocolError]]
    EventTrailers: type[Union[RequestTrailers, ResponseTrailers]]
    ReceiveTrailers: type[Union[RequestTrailers, ResponseTrailers]]

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            self.quic = yield QuicGetConnection()
            assert isinstance(self.quic, H3Connection)
            self.h3_conn = H3Connection(self.quic, enable_webtransport=False)

        else:
            assert self.quic is not None
            assert self.h3_conn is not None

            if isinstance(event, HttpEvent):
                try:

                    if isinstance(event, self.EventData):
                        self.h3_conn.send_data(
                            stream_id=event.stream_id, data=event.data, end_stream=False
                        )
                    elif isinstance(event, self.EventHeaders):
                        get_headers = (
                            get_request_headers
                            if isinstance(event, RequestHeaders)
                            else get_response_headers
                        )
                        self.h3_conn.send_headers(
                            stream_id=event.stream_id,
                            headers=(yield from get_headers(event)),
                            end_stream=event.end_stream,
                        )
                    elif isinstance(event, self.EventTrailers):
                        trailers = [*event.trailers.fields]
                        self.h3_conn.send_headers(
                            stream_id=event.stream_id, headers=trailers, end_stream=True
                        )
                    elif isinstance(event, self.EventEndOfMessage):
                        self.h3_conn.send_data(
                            stream_id=event.stream_id, data=b"", end_stream=True
                        )
                    elif isinstance(event, self.EventProtocolError):
                        self.protocol_error(event)
                    else:
                        raise AssertionError(f"Unexpected event: {event}")

                except FrameUnexpected:
                    # Http2Connection also ignores events that violate the current stream state
                    return

                # transmit buffered data and re-arm timer
                yield QuicTransmit(self.quic)

            elif isinstance(event, QuicConnectionEvent):
                for h3_event in self.h3_conn.handle_event(event.event):
                    if isinstance(h3_event, h3_events.DataReceived):
                        pass

                    elif isinstance(h3_event, h3_events.HeadersReceived):
                        pass

                    else:
                        pass

    @abstractmethod
    def protocol_error(
        self, event: Union[RequestProtocolError, ResponseProtocolError]
    ) -> None:
        yield from ()  # pragma: no cover


class Http3Server(Http3Connection):
    def __init__(self, context: context.Context):
        super().__init__(context, context.client)

    def protocol_error(
        self, event: Union[RequestProtocolError, ResponseProtocolError]
    ) -> None:
        assert self.h3_conn is not None
        assert isinstance(event, ResponseProtocolError)

        # same as HTTP/2
        code = event.code
        if code != status_codes.CLIENT_CLOSED_REQUEST:
            code = status_codes.INTERNAL_SERVER_ERROR
        self.h3_conn.send_headers(
            stream_id=event.stream_id,
            headers=[
                (b":status", b"%d" % code),
                (b"server", version.MITMPROXY.encode()),
                (b"content-type", b"text/html"),
            ],
        )
        self.h3_conn.send_data(
            stream_id=event.stream_id,
            data=format_error(code, event.message),
            end_stream=True,
        )


class Http3Client(Http3Connection):
    def __init__(self, context: context.Context):
        super().__init__(context, context.server)

    def protocol_error(
        self, event: Union[RequestProtocolError, ResponseProtocolError]
    ) -> None:
        assert isinstance(event, RequestProtocolError)
        assert self.quic is not None

        # same as HTTP/2
        code = event.code
        if code != H3ErrorCode.H3_REQUEST_CANCELLED:
            code = H3ErrorCode.H3_INTERNAL_ERROR
        self.quic.reset_stream(stream_id=event.stream_id, error_code=code)


__all__ = [
    "Http3Client",
    "Http3Server",
]
