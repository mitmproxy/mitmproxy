from mitmproxy import http

from mitmproxy.proxy2 import events


class HttpEvent(events.Event):
    flow: http.HTTPFlow

    def __init__(self, flow: http.HTTPFlow):
        self.flow = flow


class RequestHeaders(HttpEvent):
    pass


class RequestData(HttpEvent):
    pass


class RequestComplete(HttpEvent):
    pass


class ResponseHeaders(HttpEvent):
    pass


class ResponseData(HttpEvent):
    data: bytes

    def __init__(self, flow, data):
        super().__init__(flow)
        self.data = data


class ResponseComplete(HttpEvent):
    pass
