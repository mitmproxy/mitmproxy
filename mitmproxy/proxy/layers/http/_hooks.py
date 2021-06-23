from dataclasses import dataclass

from mitmproxy import http
from mitmproxy.proxy import commands


@dataclass
class HttpRequestHeadersHook(commands.StartHook):
    """
    HTTP request headers were successfully read. At this point, the body is empty.
    """
    name = "requestheaders"
    flow: http.HTTPFlow


@dataclass
class HttpRequestHook(commands.StartHook):
    """
    The full HTTP request has been read.

    Note: If request streaming is active, this event fires after the entire body has been streamed.
    HTTP trailers, if present, have not been transmitted to the server yet and can still be modified.
    Enabling streaming may cause unexpected event sequences: For example, `response` may now occur
    before `request` because the server replied with "413 Payload Too Large" during upload.
    """
    name = "request"
    flow: http.HTTPFlow


@dataclass
class HttpResponseHeadersHook(commands.StartHook):
    """
    HTTP response headers were successfully read. At this point, the body is empty.
    """
    name = "responseheaders"
    flow: http.HTTPFlow


@dataclass
class HttpResponseHook(commands.StartHook):
    """
    The full HTTP response has been read.

    Note: If response streaming is active, this event fires after the entire body has been streamed.
    HTTP trailers, if present, have not been transmitted to the client yet and can still be modified.
    """
    name = "response"
    flow: http.HTTPFlow


@dataclass
class HttpErrorHook(commands.StartHook):
    """
    An HTTP error has occurred, e.g. invalid server responses, or
    interrupted connections. This is distinct from a valid server HTTP
    error response, which is simply a response with an HTTP error code.

    Every flow will receive either an error or an response event, but not both.
    """
    name = "error"
    flow: http.HTTPFlow


@dataclass
class HttpConnectHook(commands.StartHook):
    """
    An HTTP CONNECT request was received. This event can be ignored for most practical purposes.

    This event only occurs in regular and upstream proxy modes
    when the client instructs mitmproxy to open a connection to an upstream host.
    Setting a non 2xx response on the flow will return the response to the client and abort the connection.

    CONNECT requests are HTTP proxy instructions for mitmproxy itself
    and not forwarded. They do not generate the usual HTTP handler events,
    but all requests going over the newly opened connection will.
    """
    flow: http.HTTPFlow


@dataclass
class HttpConnectUpstreamHook(commands.StartHook):
    """
    An HTTP CONNECT request is about to be sent to an upstream proxy.
    This event can be ignored for most practical purposes.

    This event can be used to set custom authentication headers for upstream proxies.

    CONNECT requests do not generate the usual HTTP handler events,
    but all requests going over the newly opened connection will.
    """
    flow: http.HTTPFlow
