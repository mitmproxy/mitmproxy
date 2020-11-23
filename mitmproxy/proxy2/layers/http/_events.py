from dataclasses import dataclass

from mitmproxy import http
from ._base import HttpEvent


@dataclass
class RequestHeaders(HttpEvent):
    request: http.HTTPRequest
    end_stream: bool
    """
    If True, we already know at this point that there is no message body. This is useful for HTTP/2, where it allows
    us to set END_STREAM on headers already (and some servers - Akamai - implicitly expect that).
    In either case, this event will nonetheless be followed by RequestEndOfMessage.
    """


@dataclass
class ResponseHeaders(HttpEvent):
    response: http.HTTPResponse
    end_stream: bool = False


@dataclass
class RequestData(HttpEvent):
    data: bytes


@dataclass
class ResponseData(HttpEvent):
    data: bytes


class RequestEndOfMessage(HttpEvent):
    pass


class ResponseEndOfMessage(HttpEvent):
    pass


@dataclass
class RequestProtocolError(HttpEvent):
    message: str
    code: int = 400


@dataclass
class ResponseProtocolError(HttpEvent):
    message: str
    code: int = 502


__all__ = [
    "HttpEvent",
    "RequestHeaders",
    "RequestData",
    "RequestEndOfMessage",
    "ResponseHeaders",
    "ResponseData",
    "ResponseEndOfMessage",
    "RequestProtocolError",
    "ResponseProtocolError",
]
