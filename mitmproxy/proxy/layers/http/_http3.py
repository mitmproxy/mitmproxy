from abc import abstractmethod
import time
from typing import Dict, Optional, Union

from aioquic.h3.connection import (
    H3Connection,
    FrameUnexpected,
    ErrorCode as H3ErrorCode,
    HeadersState as H3HeadersState,
)
from aioquic.h3 import events as h3_events
from aioquic.quic import events as quic_events
from aioquic.quic.connection import QuicConnection
from aioquic.quic.packet import QuicErrorCode

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

    ReceiveData: type[Union[RequestData, ResponseData]]
    ReceiveEndOfMessage: type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    ReceiveProtocolError: type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveTrailers: type[Union[RequestTrailers, ResponseTrailers]]

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            quic = yield QuicGetConnection(self.conn)
            assert isinstance(quic, QuicConnection)
            self.quic = quic
            self.h3_conn = H3Connection(quic, enable_webtransport=False)

        if isinstance(event, events.ConnectionClosed):
            self._handle_event = self.done

        # send mitmproxy HTTP events over the H3 connection
        elif isinstance(event, HttpEvent):
            assert self.quic is not None
            assert self.h3_conn is not None
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
                    self.h3_conn.send_headers(
                        stream_id=event.stream_id,
                        headers=[*event.trailers.fields],
                        end_stream=True,
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
                # Http2Connection also ignores HttpEvents that violate the current stream state
                return

            # transmit buffered data and re-arm timer
            yield QuicTransmit(self.quic)

        # handle events from the underlying QUIC connection
        elif isinstance(event, QuicConnectionEvent):
            assert self.quic is not None
            assert self.h3_conn is not None

            # report abrupt stream resets
            if isinstance(event, quic_events.StreamReset):
                if event.stream_id in self.h3_conn._stream:
                    try:
                        reason = H3ErrorCode(event.error_code).name
                    except ValueError:
                        try:
                            reason = QuicErrorCode(event.error_code).name
                        except ValueError:
                            reason = str(event.error_code)
                    code = (
                        status_codes.CLIENT_CLOSED_REQUEST
                        if event.error_code == H3ErrorCode.H3_REQUEST_CANCELLED
                        else self.ReceiveProtocolError.code
                    )
                    yield ReceiveHttp(
                        self.ReceiveProtocolError(
                            stream_id=event.stream_id,
                            message=f"stream reset by client ({reason})",
                            code=code,
                        )
                    )

            # report a protocol error for all remaining open streams when a connection is terminated
            elif isinstance(event, quic_events.ConnectionTerminated):
                for stream in self.h3_conn._stream.values():
                    if not stream.ended:
                        yield ReceiveHttp(
                            self.ReceiveProtocolError(
                                stream_id=stream.stream_id,
                                message=event.reason_phrase,
                                code=event.error_code,
                            )
                        )

            # forward QUIC events to the H3 connection
            for h3_event in self.h3_conn.handle_event(event.event):

                # report received data
                if isinstance(h3_event, h3_events.DataReceived):
                    yield ReceiveHttp(
                        self.ReceiveData(
                            stream_id=h3_event.stream_id, data=h3_event.data
                        )
                    )
                    if h3_event.stream_ended:
                        yield ReceiveHttp(
                            self.ReceiveEndOfMessage(stream_id=event.stream_id)
                        )

                # report headers and trailers
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
                            # this will result in a ConnectionTerminated event
                            self.quic.close(
                                error_code=H3ErrorCode.H3_GENERAL_PROTOCOL_ERROR,
                                reason_phrase=f"Invalid HTTP/3 request headers: {e}",
                            )
                        else:
                            yield ReceiveHttp(receive_event)
                        if h3_event.stream_ended:
                            yield ReceiveHttp(
                                self.ReceiveEndOfMessage(stream_id=event.stream_id)
                            )

                # we don't support push, web transport, etc.
                else:
                    yield commands.Log(
                        f"Ignored unsupported H3 event: {h3_event!r}"
                    )

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def done(self, event: events.Event) -> layer.CommandGenerator[None]:
        yield from ()

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
    ReceiveData = RequestData
    ReceiveEndOfMessage = RequestEndOfMessage
    ReceiveProtocolError = RequestProtocolError
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
    ReceiveData = ResponseData
    ReceiveEndOfMessage = ResponseEndOfMessage
    ReceiveProtocolError = ResponseProtocolError
    ReceiveTrailers = ResponseTrailers

    our_stream_id: Dict[int, int]
    their_stream_id: Dict[int, int]

    def __init__(self, context: context.Context):
        super().__init__(context, context.server)
        self.our_stream_id = {}
        self.their_stream_id = {}

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

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        # translate stream IDs just like HTTP/2 client
        if isinstance(event, HttpEvent):
            assert self.quic
            ours = self.our_stream_id.get(event.stream_id, None)
            if ours is None:
                ours = self.quic.get_next_available_stream_id()
                self.our_stream_id[event.stream_id] = ours
                self.their_stream_id[ours] = event.stream_id
            event.stream_id = ours
        for cmd in super()._handle_event(event):
            if isinstance(cmd, ReceiveHttp):
                cmd.event.stream_id = self.their_stream_id[cmd.event.stream_id]
            yield cmd


__all__ = [
    "Http3Client",
    "Http3Server",
]
