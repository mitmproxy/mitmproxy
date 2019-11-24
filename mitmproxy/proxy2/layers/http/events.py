from mitmproxy import http
from .base import HttpEvent, StreamId


class RequestHeaders(HttpEvent):
    request: http.HTTPRequest

    def __init__(self, request: http.HTTPRequest, stream_id: StreamId):
        super().__init__(stream_id)
        self.request = request


class ResponseHeaders(HttpEvent):
    response: http.HTTPResponse

    def __init__(self, response: http.HTTPResponse, stream_id: StreamId):
        super().__init__(stream_id)
        self.response = response


class RequestData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, stream_id: StreamId):
        super().__init__(stream_id)
        self.data = data


class ResponseData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, stream_id: StreamId):
        super().__init__(stream_id)
        self.data = data


class RequestEndOfMessage(HttpEvent):
    pass


class ResponseEndOfMessage(HttpEvent):
    pass


__all__ = [
    "HttpEvent",
    "RequestHeaders",
    "RequestData",
    "RequestEndOfMessage",
    "ResponseHeaders",
    "ResponseData",
    "ResponseEndOfMessage",
]
