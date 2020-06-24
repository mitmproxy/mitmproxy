from mitmproxy import http
from mitmproxy.proxy2 import commands


class HttpRequestHeadersHook(commands.Hook):
    name = "requestheaders"
    flow: http.HTTPFlow


class HttpRequestHook(commands.Hook):
    name = "request"
    flow: http.HTTPFlow


class HttpResponseHook(commands.Hook):
    name = "response"
    flow: http.HTTPFlow


class HttpResponseHeadersHook(commands.Hook):
    name = "responseheaders"
    flow: http.HTTPFlow


class HttpConnectHook(commands.Hook):
    flow: http.HTTPFlow


class HttpErrorHook(commands.Hook):
    name = "error"
    flow: http.HTTPFlow
