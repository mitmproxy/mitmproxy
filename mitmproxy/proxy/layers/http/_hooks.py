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

    Note: This event fires immediately after requestheaders if the request body is streamed.
    This ensures that requestheaders -> request -> responseheaders -> response happen in that order.
    """
    name = "request"
    flow: http.HTTPFlow


@dataclass
class HttpResponseHeadersHook(commands.StartHook):
    """
    The full HTTP response has been read.
    """
    name = "responseheaders"
    flow: http.HTTPFlow


@dataclass
class HttpResponseHook(commands.StartHook):
    """
    HTTP response headers were successfully read. At this point, the body is empty.

    Note: If response streaming is active, this event fires after the entire body has been streamed.
    """
    name = "response"
    flow: http.HTTPFlow


@dataclass
class HttpRequestTrailersHook(commands.StartHook):
    """
    The HTTP request trailers has been read.
    HTTP trailers are a rarely-used feature in the HTTP specification
    which allows peers to send additional headers after the message body.
    This is useful for metadata that is dynamically generated while
    the message body is sent, for example a digital signature
    or post-processing status.
    """
    name = "requesttrailers"
    flow: http.HTTPFlow


@dataclass
class HttpResponseTrailersHook(commands.StartHook):
    """
    The HTTP response trailers has been read.
    HTTP trailers are a rarely-used feature in the HTTP specification
    which allows peers to send additional headers after the message body.
    This is useful for metadata that is dynamically generated while
    the message body is sent, for example a digital signature
    or post-processing status.
    """
    name = "responsetrailers"
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
