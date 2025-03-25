import enum
import typing
from dataclasses import dataclass

from ._base import HttpEvent
from mitmproxy import http
from mitmproxy.http import HTTPFlow
from mitmproxy.net.http import status_codes


@dataclass
class RequestHeaders(HttpEvent):
    request: http.Request
    end_stream: bool
    """
    If True, we already know at this point that there is no message body. This is useful for HTTP/2, where it allows
    us to set END_STREAM on headers already (and some servers - Akamai - implicitly expect that).
    In either case, this event will nonetheless be followed by RequestEndOfMessage.
    """
    replay_flow: HTTPFlow | None = None
    """If set, the current request headers belong to a replayed flow, which should be reused."""


@dataclass
class ResponseHeaders(HttpEvent):
    response: http.Response
    end_stream: bool = False


# explicit constructors below to facilitate type checking in _http1/_http2


@dataclass
class RequestData(HttpEvent):
    data: bytes

    def __init__(self, stream_id: int, data: bytes):
        self.stream_id = stream_id
        self.data = data


@dataclass
class ResponseData(HttpEvent):
    data: bytes

    def __init__(self, stream_id: int, data: bytes):
        self.stream_id = stream_id
        self.data = data


@dataclass
class RequestTrailers(HttpEvent):
    trailers: http.Headers

    def __init__(self, stream_id: int, trailers: http.Headers):
        self.stream_id = stream_id
        self.trailers = trailers


@dataclass
class ResponseTrailers(HttpEvent):
    trailers: http.Headers

    def __init__(self, stream_id: int, trailers: http.Headers):
        self.stream_id = stream_id
        self.trailers = trailers


@dataclass
class RequestEndOfMessage(HttpEvent):
    def __init__(self, stream_id: int):
        self.stream_id = stream_id


@dataclass
class ResponseEndOfMessage(HttpEvent):
    def __init__(self, stream_id: int):
        self.stream_id = stream_id


class ErrorCode(enum.Enum):
    GENERIC_CLIENT_ERROR = 1
    GENERIC_SERVER_ERROR = 2
    REQUEST_TOO_LARGE = 3
    RESPONSE_TOO_LARGE = 4
    CONNECT_FAILED = 5
    PASSTHROUGH_CLOSE = 6
    KILL = 7
    HTTP_1_1_REQUIRED = 8
    """Client should fall back to HTTP/1.1 to perform request."""
    DESTINATION_UNKNOWN = 9
    """Proxy does not know where to send request to."""
    CLIENT_DISCONNECTED = 10
    """Client disconnected before receiving entire response."""
    CANCEL = 11
    """Client or server cancelled h2/h3 stream."""
    REQUEST_VALIDATION_FAILED = 12
    RESPONSE_VALIDATION_FAILED = 13

    def http_status_code(self) -> int | None:
        match self:
            # Client Errors
            case (
                ErrorCode.GENERIC_CLIENT_ERROR
                | ErrorCode.REQUEST_VALIDATION_FAILED
                | ErrorCode.DESTINATION_UNKNOWN
            ):
                return status_codes.BAD_REQUEST
            case ErrorCode.REQUEST_TOO_LARGE:
                return status_codes.PAYLOAD_TOO_LARGE
            case (
                ErrorCode.CONNECT_FAILED
                | ErrorCode.GENERIC_SERVER_ERROR
                | ErrorCode.RESPONSE_VALIDATION_FAILED
                | ErrorCode.RESPONSE_TOO_LARGE
            ):
                return status_codes.BAD_GATEWAY
            case (
                ErrorCode.PASSTHROUGH_CLOSE
                | ErrorCode.KILL
                | ErrorCode.HTTP_1_1_REQUIRED
                | ErrorCode.CLIENT_DISCONNECTED
                | ErrorCode.CANCEL
            ):
                return None
            case other:  # pragma: no cover
                typing.assert_never(other)


@dataclass
class RequestProtocolError(HttpEvent):
    message: str
    code: ErrorCode = ErrorCode.GENERIC_CLIENT_ERROR

    def __init__(self, stream_id: int, message: str, code: ErrorCode):
        assert isinstance(code, ErrorCode)
        self.stream_id = stream_id
        self.message = message
        self.code = code


@dataclass
class ResponseProtocolError(HttpEvent):
    message: str
    code: ErrorCode = ErrorCode.GENERIC_SERVER_ERROR

    def __init__(self, stream_id: int, message: str, code: ErrorCode):
        assert isinstance(code, ErrorCode)
        self.stream_id = stream_id
        self.message = message
        self.code = code


__all__ = [
    "ErrorCode",
    "HttpEvent",
    "RequestHeaders",
    "RequestData",
    "RequestEndOfMessage",
    "ResponseHeaders",
    "ResponseData",
    "RequestTrailers",
    "ResponseTrailers",
    "ResponseEndOfMessage",
    "RequestProtocolError",
    "ResponseProtocolError",
]
