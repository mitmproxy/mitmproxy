from __future__ import (absolute_import, print_function, division)
import Cookie
import copy
from email.utils import parsedate_tz, formatdate, mktime_tz
import time

from libmproxy import utils
from netlib import encoding
from netlib.http import status_codes, Headers, Request, Response, CONTENT_MISSING, decoded
from netlib.tcp import Address
from .. import version, stateobject
from .flow import Flow


class MessageMixin(stateobject.StateObject):
    _stateobject_attributes = dict(
        http_version=bytes,
        headers=Headers,
        timestamp_start=float,
        timestamp_end=float
    )
    _stateobject_long_attributes = {"body"}

    def get_state(self, short=False):
        ret = super(MessageMixin, self).get_state(short)
        if short:
            if self.content:
                ret["contentLength"] = len(self.content)
            elif self.content == CONTENT_MISSING:
                ret["contentLength"] = None
            else:
                ret["contentLength"] = 0
        return ret

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

    def decode(self):
        """
            Decodes body based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.

            Returns True if decoding succeeded, False otherwise.
        """
        ce = self.headers.get("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return False
        data = encoding.decode(ce, self.content)
        if data is None:
            return False
        self.content = data
        self.headers.pop("content-encoding", None)
        return True

    def encode(self, e):
        """
            Encodes body with the encoding e, where e is "gzip", "deflate"
            or "identity".
        """
        # FIXME: Error if there's an existing encoding header?
        self.content = encoding.encode(e, self.content)
        self.headers["content-encoding"] = e

    def copy(self):
        c = copy.copy(self)
        if hasattr(self, "data"):  # FIXME remove condition
            c.data = copy.copy(self.data)

        c.headers = self.headers.copy()
        return c

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the message. Encoded body will be decoded
            before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, count = utils.safe_subn(
                pattern, repl, self.content, *args, **kwargs
            )
        fields = []
        for name, value in self.headers.fields:
            name, c = utils.safe_subn(pattern, repl, name, *args, **kwargs)
            count += c
            value, c = utils.safe_subn(pattern, repl, value, *args, **kwargs)
            count += c
            fields.append([name, value])
        self.headers.fields = fields
        return count


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

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        form_in: The request form which mitmproxy has received. The following
        values are possible:

             - relative (GET /index.html, OPTIONS *) (covers origin form and
               asterisk form)
             - absolute (GET http://example.com:80/index.html)
             - authority-form (CONNECT example.com:443)
             Details: http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-25#section-5.3

        form_out: The request form which mitmproxy will send out to the
        destination

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
            form_out=None,
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
        self.form_out = form_out or first_line_format  # FIXME remove

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False

        # Is this request replayed?
        self.is_replay = False

    _stateobject_attributes = MessageMixin._stateobject_attributes.copy()
    _stateobject_attributes.update(
        content=bytes,
        first_line_format=str,
        method=bytes,
        scheme=bytes,
        host=bytes,
        port=int,
        path=bytes,
        form_out=str,
        is_replay=bool
    )

    @classmethod
    def from_state(cls, state):
        f = cls(
            None,
            b"",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None)
        f.load_state(state)
        return f

    @classmethod
    def from_protocol(
            self,
            protocol,
            *args,
            **kwargs
    ):
        req = protocol.read_request(*args, **kwargs)
        return self.wrap(req)

    @classmethod
    def wrap(self, request):
        req = HTTPRequest(
            first_line_format=request.form_in,
            method=request.method,
            scheme=request.scheme,
            host=request.host,
            port=request.port,
            path=request.path,
            http_version=request.http_version,
            headers=request.headers,
            content=request.content,
            timestamp_start=request.timestamp_start,
            timestamp_end=request.timestamp_end,
            form_out=(request.form_out if hasattr(request, 'form_out') else None),
        )
        if hasattr(request, 'stream_id'):
            req.stream_id = request.stream_id
        return req

    def __hash__(self):
        return id(self)

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in the headers, the
            request path and the body of the request. Encoded content will be
            decoded before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = MessageMixin.replace(self, pattern, repl, *args, **kwargs)
        self.path, pc = utils.safe_subn(
            pattern, repl, self.path, *args, **kwargs
        )
        c += pc
        return c


class HTTPResponse(MessageMixin, Response):
    """
    An HTTP response.

    Exposes the following attributes:

        http_version: HTTP version, e.g. "HTTP/1.1"

        status_code: HTTP response status code

        msg: HTTP response message

        headers: Headers object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

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
        self.is_replay = False
        self.stream = False

    _stateobject_attributes = MessageMixin._stateobject_attributes.copy()
    _stateobject_attributes.update(
        body=bytes,
        status_code=int,
        msg=bytes
    )

    @classmethod
    def from_state(cls, state):
        f = cls(None, None, None, None, None)
        f.load_state(state)
        return f

    @classmethod
    def from_protocol(
            self,
            protocol,
            *args,
            **kwargs
    ):
        resp = protocol.read_response(*args, **kwargs)
        return self.wrap(resp)

    @classmethod
    def wrap(self, response):
        resp = HTTPResponse(
            http_version=response.http_version,
            status_code=response.status_code,
            reason=response.reason,
            headers=response.headers,
            content=response.content,
            timestamp_start=response.timestamp_start,
            timestamp_end=response.timestamp_end,
        )
        if hasattr(response, 'stream_id'):
            resp.stream_id = response.stream_id
        return resp

    def _refresh_cookie(self, c, delta):
        """
            Takes a cookie string c and a time delta in seconds, and returns
            a refreshed cookie string.
        """
        try:
            c = Cookie.SimpleCookie(str(c))
        except Cookie.CookieError:
            raise ValueError("Invalid Cookie")
        for i in c.values():
            if "expires" in i:
                d = parsedate_tz(i["expires"])
                if d:
                    d = mktime_tz(d) + delta
                    i["expires"] = formatdate(d)
                else:
                    # This can happen when the expires tag is invalid.
                    # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                    # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                    # strictly correct according to the cookie spec. Browsers
                    # appear to parse this tolerantly - maybe we should too.
                    # For now, we just ignore this.
                    del i["expires"]
        ret = c.output(header="").strip()
        if not ret:
            raise ValueError("Invalid Cookie")
        return ret

    def refresh(self, now=None):
        """
            This fairly complex and heuristic function refreshes a server
            response for replay.

                - It adjusts date, expires and last-modified headers.
                - It adjusts cookie expiration.
        """
        if not now:
            now = time.time()
        delta = now - self.timestamp_start
        refresh_headers = [
            "date",
            "expires",
            "last-modified",
        ]
        for i in refresh_headers:
            if i in self.headers:
                d = parsedate_tz(self.headers[i])
                if d:
                    new = mktime_tz(d) + delta
                    self.headers[i] = formatdate(new)
        c = []
        for set_cookie_header in self.headers.get_all("set-cookie"):
            try:
                refreshed = self._refresh_cookie(set_cookie_header, delta)
            except ValueError:
                refreshed = set_cookie_header
            c.append(refreshed)
        if c:
            self.headers.set_all("set-cookie", c)


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
        f.load_state(state)
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
    response = status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>%d %s</title>
            </head>
            <body>%s</body>
        </html>
    """.strip() % (status_code, response, message)

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
        "authority", "CONNECT", None, address.host, address.port, None, b"HTTP/1.1",
        Headers(), ""
    )


def make_connect_response(http_version):
    headers = Headers(
        Proxy_Agent=version.NAMEVERSION
    )
    return HTTPResponse(
        http_version,
        200,
        "Connection established",
        headers,
        "",
    )

expect_continue_response = HTTPResponse(b"HTTP/1.1", 100, "Continue", Headers(), b"")