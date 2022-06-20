from abc import abstractmethod
import time
from typing import Optional, Union

from aioquic.quic.connection import QuicConnection
from aioquic.h3.connection import (
    H3Connection,
    FrameUnexpected,
    ErrorCode as H3ErrorCode,
    HeadersState as H3HeadersState,
)
from aioquic.h3 import events as h3_events

from mitmproxy import http, version
from mitmproxy.net.http import status_codes
from mitmproxy.proxy import commands, context, events, layer
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
    ReceiveHttp,
    format_error,
)
from ._http2 import (
    format_h2_request_headers,
    format_h2_response_headers,
    parse_h2_request_headers,
    parse_h2_response_headers,
)


class Http3Connection(HttpConnection):
    quic: Optional[QuicConnection] = None
    h3_conn: Optional[H3Connection] = None

    ReceiveTrailers: type[Union[RequestTrailers, ResponseTrailers]]

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            quic = yield QuicGetConnection(self.conn)
            assert isinstance(quic, QuicConnection)
            self.quic = quic
            self.h3_conn = H3Connection(quic, enable_webtransport=False)

        else:
            assert self.quic is not None
            assert self.h3_conn is not None

            if isinstance(event, HttpEvent):
                try:

                    if isinstance(event, (RequestData, ResponseData)):
                        self.h3_conn.send_data(
                            stream_id=event.stream_id, data=event.data, end_stream=False
                        )
                    elif isinstance(event, (RequestHeaders, ResponseHeaders)):
                        self.h3_conn.send_headers(
                            stream_id=event.stream_id,
                            headers=(
                                yield from (
                                    format_h2_request_headers(event)
                                    if isinstance(event, RequestHeaders)
                                    else format_h2_response_headers(event)
                                )
                            ),
                            end_stream=event.end_stream,
                        )
                    elif isinstance(event, (RequestTrailers, ResponseTrailers)):
                        trailers = [*event.trailers.fields]
                        self.h3_conn.send_headers(
                            stream_id=event.stream_id, headers=trailers, end_stream=True
                        )
                    elif isinstance(event, (RequestEndOfMessage, ResponseEndOfMessage)):
                        self.h3_conn.send_data(
                            stream_id=event.stream_id, data=b"", end_stream=True
                        )
                    elif isinstance(
                        event, (RequestProtocolError, ResponseProtocolError)
                    ):
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

                    # handle headers and trailers
                    elif isinstance(h3_event, h3_events.HeadersReceived):
                        if (
                            self.h3_conn._stream[h3_event.stream_id].headers_recv_state
                            is H3HeadersState.AFTER_TRAILERS
                        ):
                            yield ReceiveHttp(
                                self.ReceiveTrailers(
                                    stream_id=h3_event.stream_id,
                                    trailers=http.Headers(h3_event.headers),
                                )
                            )
                        else:
                            try:
                                receive_event = self.headers_received(h3_event)
                            except ValueError as e:
                                # TODO
                                pass
                            else:
                                yield ReceiveHttp(receive_event)

                    # we don't support push, web transport, etc.
                    else:
                        yield commands.Log(
                            f"Ignored unsupported H3 event: {h3_event!r}"
                        )

    @abstractmethod
    def protocol_error(
        self, event: Union[RequestProtocolError, ResponseProtocolError]
    ) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def headers_received(
        self, event: h3_events.HeadersReceived
    ) -> Union[RequestHeaders, ResponseHeaders]:
        pass  # pragma: no cover


class Http3Server(Http3Connection):
    ReceiveTrailers = RequestTrailers

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

    def headers_received(
        self, event: h3_events.HeadersReceived
    ) -> Union[RequestHeaders, ResponseHeaders]:
        # same as HTTP/2
        (
            host,
            port,
            method,
            scheme,
            authority,
            path,
            headers,
        ) = parse_h2_request_headers(event)
        request = http.Request(
            host=host,
            port=port,
            method=method,
            scheme=scheme,
            authority=authority,
            path=path,
            http_version=b"HTTP/3",
            headers=headers,
            content=None,
            trailers=None,
            timestamp_start=time.time(),
            timestamp_end=None,
        )
        return RequestHeaders(
            stream_id=event.stream_id, request=request, end_stream=event.stream_ended
        )


class Http3Client(Http3Connection):
    ReceiveTrailers = ResponseTrailers

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

    def headers_received(
        self, event: h3_events.HeadersReceived
    ) -> Union[RequestHeaders, ResponseHeaders]:
        # same as HTTP/2
        status_code, headers = parse_h2_response_headers(event.headers)
        response = http.Response(
            http_version=b"HTTP/3",
            status_code=status_code,
            reason=b"",
            headers=headers,
            content=None,
            trailers=None,
            timestamp_start=time.time(),
            timestamp_end=None,
        )
        return ResponseHeaders(
            stream_id=event.stream_id, response=response, end_stream=event.stream_ended
        )


__all__ = [
    "Http3Client",
    "Http3Server",
]
