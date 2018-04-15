import html
from typing import Optional

from mitmproxy import flow

from mitmproxy.net import http
from mitmproxy import version
from mitmproxy import connections  # noqa


class HTTPRequest(http.Request):

    """
    A mitmproxy HTTP request.
    """

    # This is a very thin wrapper on top of :py:class:`mitmproxy.net.http.Request` and
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
        # Is this request replayed?
        self.is_replay = is_replay
        self.stream = None

    def get_state(self):
        state = super().get_state()
        state["is_replay"] = self.is_replay
        return state

    def set_state(self, state):
        state = state.copy()
        self.is_replay = state.pop("is_replay")
        super().set_state(state)

    @classmethod
    def wrap(self, request):
        """
        Wraps an existing :py:class:`mitmproxy.net.http.Request`.
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
    # This is a very thin wrapper on top of :py:class:`mitmproxy.net.http.Response` and
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
        self.stream = None

    @classmethod
    def wrap(self, response):
        """
        Wraps an existing :py:class:`mitmproxy.net.http.Response`.
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

    def __init__(self, client_conn, server_conn, live=None, mode="regular"):
        super().__init__("http", client_conn, server_conn, live)

        self.request: HTTPRequest = None
        """ :py:class:`HTTPRequest` object """
        self.response: HTTPResponse = None
        """ :py:class:`HTTPResponse` object """
        self.error: flow.Error = None
        """ :py:class:`Error` object

        Note that it's possible for a Flow to have both a response and an error
        object. This might happen, for instance, when a response was received
        from the server, but there was an error sending it back to the client.
        """
        self.server_conn: connections.ServerConnection = server_conn
        """ :py:class:`ServerConnection` object """
        self.client_conn: connections.ClientConnection = client_conn
        """:py:class:`ClientConnection` object """
        self.intercepted: bool = False
        """ Is this flow currently being intercepted? """
        self.mode = mode
        """ What mode was the proxy layer in when receiving this request? """

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    # mypy doesn't support update with kwargs
    _stateobject_attributes.update(dict(
        request=HTTPRequest,
        response=HTTPResponse,
        mode=str
    ))

    def __repr__(self):
        s = "<HTTPFlow"
        for a in ("request", "response", "error", "client_conn", "server_conn"):
            if getattr(self, a, False):
                s += "\r\n  %s = {flow.%s}" % (a, a)
        s += ">"
        return s.format(flow=self)

    def copy(self):
        f = super().copy()
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


def make_error_response(
        status_code: int,
        message: str="",
        headers: Optional[http.Headers]=None,
) -> HTTPResponse:
    reason = http.status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>{status_code} {reason}</title>
            </head>
            <body>
            <h1>{status_code} {reason}</h1>
            <p>{message}</p>
            </body>
        </html>
    """.strip().format(
        status_code=status_code,
        reason=reason,
        message=html.escape(message),
    ).encode("utf8", "replace")

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
        reason,
        headers,
        body,
    )


def make_connect_request(address):
    return HTTPRequest(
        "authority", b"CONNECT", None, address[0], address[1], None, b"HTTP/1.1",
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
