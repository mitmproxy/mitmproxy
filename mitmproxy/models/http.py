from __future__ import absolute_import, print_function, division

import cgi

from mitmproxy.models import flow
from netlib import http
from netlib import version
from netlib import tcp


class HTTPRequest(http.Request):

    """
    A mitmproxy HTTP request.
    """

    # This is a very thin wrapper on top of :py:class:`netlib.http.Request` and
    # may be removed in the future.

    def __init__(
            self,
            first_line_format,
            method,
            scheme,
            host,
            port,
            path,
            http_version,
            headers,
            content,
            timestamp_start=None,
            timestamp_end=None,
            is_replay=False,
            stickycookie=False,
            stickyauth=False,
    ):
        http.Request.__init__(
            self,
            first_line_format,
            method,
            scheme,
            host,
            port,
            path,
            http_version,
            headers,
            content,
            timestamp_start,
            timestamp_end,
        )

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = stickycookie
        self.stickyauth = stickyauth

        # Is this request replayed?
        self.is_replay = is_replay

    def get_state(self):
        state = super(HTTPRequest, self).get_state()
        state.update(
            stickycookie=self.stickycookie,
            stickyauth=self.stickyauth,
            is_replay=self.is_replay,
        )
        return state

    def set_state(self, state):
        self.stickycookie = state.pop("stickycookie")
        self.stickyauth = state.pop("stickyauth")
        self.is_replay = state.pop("is_replay")
        super(HTTPRequest, self).set_state(state)

    @classmethod
    def wrap(self, request):
        """
        Wraps an existing :py:class:`netlib.http.Request`.
        """
        req = HTTPRequest(
            first_line_format=request.data.first_line_format,
            method=request.data.method,
            scheme=request.data.scheme,
            host=request.data.host,
            port=request.data.port,
            path=request.data.path,
            http_version=request.data.http_version,
            headers=request.data.headers,
            content=request.data.content,
            timestamp_start=request.data.timestamp_start,
            timestamp_end=request.data.timestamp_end,
        )
        return req

    def __hash__(self):
        return id(self)


class HTTPResponse(http.Response):

    """
    A mitmproxy HTTP response.
    """
    # This is a very thin wrapper on top of :py:class:`netlib.http.Response` and
    # may be removed in the future.

    def __init__(
            self,
            http_version,
            status_code,
            reason,
            headers,
            content,
            timestamp_start=None,
            timestamp_end=None,
            is_replay=False
    ):
        http.Response.__init__(
            self,
            http_version,
            status_code,
            reason,
            headers,
            content,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        # Is this request replayed?
        self.is_replay = is_replay
        self.stream = False

    @classmethod
    def wrap(self, response):
        """
        Wraps an existing :py:class:`netlib.http.Response`.
        """
        resp = HTTPResponse(
            http_version=response.data.http_version,
            status_code=response.data.status_code,
            reason=response.data.reason,
            headers=response.data.headers,
            content=response.data.content,
            timestamp_start=response.data.timestamp_start,
            timestamp_end=response.data.timestamp_end,
        )
        return resp


class HTTPFlow(flow.Flow):

    """
    An HTTPFlow is a collection of objects representing a single HTTP
    transaction.
    """

    def __init__(self, client_conn, server_conn, live=None):
        super(HTTPFlow, self).__init__("http", client_conn, server_conn, live)

        self.request = None
        """ :py:class:`HTTPRequest` object """
        self.response = None
        """ :py:class:`HTTPResponse` object """
        self.error = None
        """ :py:class:`Error` object

        Note that it's possible for a Flow to have both a response and an error
        object. This might happen, for instance, when a response was received
        from the server, but there was an error sending it back to the client.
        """
        self.server_conn = server_conn
        """ :py:class:`ServerConnection` object """
        self.client_conn = client_conn
        """:py:class:`ClientConnection` object """
        self.intercepted = False
        """ Is this flow currently being intercepted? """

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        request=HTTPRequest,
        response=HTTPResponse
    )

    def __repr__(self):
        s = "<HTTPFlow"
        for a in ("request", "response", "error", "client_conn", "server_conn"):
            if getattr(self, a, False):
                s += "\r\n  %s = {flow.%s}" % (a, a)
        s += ">"
        return s.format(flow=self)

    def copy(self):
        f = super(HTTPFlow, self).copy()
        if self.request:
            f.request = self.request.copy()
        if self.response:
            f.response = self.response.copy()
        return f

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both request and
            response of the flow. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = self.request.replace(pattern, repl, *args, **kwargs)
        if self.response:
            c += self.response.replace(pattern, repl, *args, **kwargs)
        return c


def make_error_response(status_code, message, headers=None):
    response = http.status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>%d %s</title>
            </head>
            <body>%s</body>
        </html>
    """.strip() % (status_code, response, cgi.escape(message))
    body = body.encode("utf8", "replace")

    if not headers:
        headers = http.Headers(
            Server=version.MITMPROXY,
            Connection="close",
            Content_Length=str(len(body)),
            Content_Type="text/html"
        )

    return HTTPResponse(
        b"HTTP/1.1",
        status_code,
        response,
        headers,
        body,
    )


def make_connect_request(address):
    address = tcp.Address.wrap(address)
    return HTTPRequest(
        "authority", b"CONNECT", None, address.host, address.port, None, b"HTTP/1.1",
        http.Headers(), b""
    )


def make_connect_response(http_version):
    # Do not send any response headers as it breaks proxying non-80 ports on
    # Android emulators using the -http-proxy option.
    return HTTPResponse(
        http_version,
        200,
        b"Connection established",
        http.Headers(),
        b"",
    )

expect_continue_response = HTTPResponse(
    b"HTTP/1.1", 100, b"Continue", http.Headers(), b""
)
