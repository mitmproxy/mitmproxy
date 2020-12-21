"""HTTP-specific events."""
import mitmproxy.http


class Events:
    def http_connect(self, flow: mitmproxy.http.HTTPFlow):
        """
        An HTTP CONNECT request was received. Setting a non 2xx response on
        the flow will return the response to the client abort the
        connection. CONNECT requests and responses do not generate the usual
        HTTP handler events. CONNECT requests are only valid in regular and
        upstream proxy modes.
        """

    def requestheaders(self, flow: mitmproxy.http.HTTPFlow):
        """
        HTTP request headers were successfully read. At this point, the body
        is empty.
        """

    def request(self, flow: mitmproxy.http.HTTPFlow):
        """
        The full HTTP request has been read.
        """

    def responseheaders(self, flow: mitmproxy.http.HTTPFlow):
        """
        HTTP response headers were successfully read. At this point, the body
        is empty.
        """

    def response(self, flow: mitmproxy.http.HTTPFlow):
        """
        The full HTTP response has been read.
        """

    def error(self, flow: mitmproxy.http.HTTPFlow):
        """
        An HTTP error has occurred, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP
        error response, which is simply a response with an HTTP error code.
        """
