from __future__ import (absolute_import, print_function, division)
import cgi
import copy
import warnings
from email.utils import parsedate_tz, formatdate, mktime_tz
import time

from netlib import encoding
from netlib.http import status_codes, Headers, Request, Response, decoded
from netlib.tcp import Address
from .. import utils
from .. import version
from .flow import Flow


class MessageMixin(object):

    def get_decoded_content(self):
        """
            Returns the decoded content based on the current Content-Encoding
            header.
            Doesn't change the message iteself or its headers.
        """
        ce = self.headers.get("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return self.content
        return encoding.decode(ce, self.content)


class HTTPRequest(MessageMixin, Request):

    """
    An HTTP request.

    Exposes the following attributes:

        method: HTTP method

        scheme: URL scheme (http/https)

        host: Target hostname of the request. This is not neccessarily the
        directy upstream server (which could be another proxy), but it's always
        the target server we want to reach at the end. This attribute is either
        inferred from the request itself (absolute-form, authority-form) or from
        the connection metadata (e.g. the host in reverse proxy mode).

        port: Destination port

        path: Path portion of the URL (not present in authority-form)

        http_version: HTTP version, e.g. "HTTP/1.1"

        headers: Headers object

        content: Content of the request, the value is None if there is content
        associated, but not present.

        first_line_format: The request form. The following values are possible:

             - relative (GET /index.html, OPTIONS *) (origin form or asterisk form)
             - absolute (GET http://example.com:80/index.html)
             - authority-form (CONNECT example.com:443)
             Details: http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-25#section-5.3

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

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
        Request.__init__(
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
            stickycookie = self.stickycookie,
            stickyauth = self.stickyauth,
            is_replay = self.is_replay,
        )
        return state

    def set_state(self, state):
        self.stickycookie = state.pop("stickycookie")
        self.stickyauth = state.pop("stickyauth")
        self.is_replay = state.pop("is_replay")
        super(HTTPRequest, self).set_state(state)

    @classmethod
    def wrap(self, request):
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

class HTTPResponse(MessageMixin, Response):

    """
    An HTTP response.

    Exposes the following attributes:

        http_version: HTTP version, e.g. "HTTP/1.1"

        status_code: HTTP response status code

        msg: HTTP response message

        headers: Headers object

        content: Content of the response, the value is None if there is content
        associated, but not present.

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(
            self,
            http_version,
            status_code,
            reason,
            headers,
            content,
            timestamp_start=None,
            timestamp_end=None,
            is_replay = False
    ):
        Response.__init__(
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


class HTTPFlow(Flow):

    """
    A HTTPFlow is a collection of objects representing a single HTTP
    transaction.

    Attributes:
        request: HTTPRequest object
        response: HTTPResponse object
        error: Error object
        server_conn: ServerConnection object
        client_conn: ClientConnection object
        intercepted: Is this flow currently being intercepted?
        live: Does this flow have a live client connection?

    Note that it's possible for a Flow to have both a response and an error
    object. This might happen, for instance, when a response was received
    from the server, but there was an error sending it back to the client.
    """

    def __init__(self, client_conn, server_conn, live=None):
        super(HTTPFlow, self).__init__("http", client_conn, server_conn, live)
        self.request = None
        """@type: HTTPRequest"""
        self.response = None
        """@type: HTTPResponse"""

    _stateobject_attributes = Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        request=HTTPRequest,
        response=HTTPResponse
    )

    @classmethod
    def from_state(cls, state):
        f = cls(None, None)
        f.set_state(state)
        return f

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

    def match(self, f):
        """
            Match this flow against a compiled filter expression. Returns True
            if matched, False if not.

            If f is a string, it will be compiled as a filter expression. If
            the expression is invalid, ValueError is raised.
        """
        if isinstance(f, basestring):
            from .. import filt

            f = filt.parse(f)
            if not f:
                raise ValueError("Invalid filter expression.")
        if f:
            return f(self)
        return True

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
    response = status_codes.RESPONSES.get(status_code, "Unknown").encode()
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
        headers = Headers(
            Server=version.NAMEVERSION,
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
    address = Address.wrap(address)
    return HTTPRequest(
        "authority", b"CONNECT", None, address.host, address.port, None, b"HTTP/1.1",
        Headers(), b""
    )


def make_connect_response(http_version):
    # Do not send any response headers as it breaks proxying non-80 ports on
    # Android emulators using the -http-proxy option.
    return HTTPResponse(
        http_version,
        200,
        b"Connection established",
        Headers(),
        b"",
    )

expect_continue_response = HTTPResponse(b"HTTP/1.1", 100, b"Continue", Headers(), b"")
