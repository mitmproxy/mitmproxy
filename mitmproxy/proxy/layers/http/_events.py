from dataclasses import dataclass
from typing import Optional

from mitmproxy import http
from mitmproxy.http import HTTPFlow
from ._base import HttpEvent


@dataclass
class RequestHeaders(HttpEvent):
    request: http.Request
    end_stream: bool
    """
    If True, we already know at this point that there is no message body. This is useful for HTTP/2, where it allows
    us to set END_STREAM on headers already (and some servers - Akamai - implicitly expect that).
    In either case, this event will nonetheless be followed by RequestEndOfMessage.
    """
    replay_flow: Optional[HTTPFlow] = None
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


@dataclass
class RequestProtocolError(HttpEvent):
    message: str
    code: int = 400

    def __init__(self, stream_id: int, message: str, code: int = 400):
        self.stream_id = stream_id
        self.message = message
        self.code = code


@dataclass
class ResponseProtocolError(HttpEvent):
    message: str
    code: int = 502

    def __init__(self, stream_id: int, message: str, code: int = 502):
        self.stream_id = stream_id
        self.message = message
        self.code = code


__all__ = [
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
