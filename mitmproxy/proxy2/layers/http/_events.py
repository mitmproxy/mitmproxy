from dataclasses import dataclass

from mitmproxy import http
from ._base import HttpEvent


@dataclass
class RequestHeaders(HttpEvent):
    request: http.HTTPRequest


@dataclass
class ResponseHeaders(HttpEvent):
    response: http.HTTPResponse


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
