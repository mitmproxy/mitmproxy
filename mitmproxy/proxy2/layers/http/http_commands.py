from mitmproxy import http

from mitmproxy.proxy2 import commands


class HttpCommand(commands.Command):
    flow: http.HTTPFlow

    def __init__(self, flow: http.HTTPFlow):
        self.flow = flow

class SendRequestHeaders(HttpCommand):
    pass


class SendRequestData(HttpCommand):
    pass


class SendRequestComplete(HttpCommand):
    pass


class SendResponseHeaders(HttpCommand):
    pass


class SendResponseData(HttpCommand):
    data: bytes

    def __init__(self, flow, data):
        super().__init__(flow)
        self.data = data


class SendResponseComplete(HttpCommand):
    pass
