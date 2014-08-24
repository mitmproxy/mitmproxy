from __future__ import absolute_import
import Cookie, urllib, urlparse, time, copy
from email.utils import parsedate_tz, formatdate, mktime_tz
import threading
from netlib import http, tcp, http_status
import netlib.utils
from netlib.odict import ODict, ODictCaseless
from .primitives import KILL, ProtocolHandler, LiveConnection, Flow, Error
from ..proxy.connection import ServerConnection
from .. import encoding, utils, controller, stateobject, proxy

HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_MISSING = 0


def get_line(fp):
    """
    Get a line, possibly preceded by a blank.
    """
    line = fp.readline()
    if line == "\r\n" or line == "\n":  # Possible leftover from previous message
        line = fp.readline()
    if line == "":
        raise tcp.NetLibDisconnect
    return line


def send_connect_request(conn, host, port):
    upstream_request = HTTPRequest("authority", "CONNECT", None, host, port, None,
                                   (1, 1), ODictCaseless(), "")
    conn.send(upstream_request._assemble())
    resp = HTTPResponse.from_stream(conn.rfile, upstream_request.method)
    if resp.code != 200:
        raise proxy.ProxyError(resp.code,
                               "Cannot establish SSL " +
                               "connection with upstream proxy: \r\n" +
                               str(resp._assemble()))
    return resp


class decoded(object):
    """
    A context manager that decodes a request or response, and then
    re-encodes it with the same encoding after execution of the block.

    Example:
    with decoded(request):
        request.content = request.content.replace("foo", "bar")
    """

    def __init__(self, o):
        self.o = o
        ce = o.headers.get_first("content-encoding")
        if ce in encoding.ENCODINGS:
            self.ce = ce
        else:
            self.ce = None

    def __enter__(self):
        if self.ce:
            self.o.decode()

    def __exit__(self, type, value, tb):
        if self.ce:
            self.o.encode(self.ce)


class HTTPMessage(stateobject.SimpleStateObject):
    def __init__(self, httpversion, headers, content, timestamp_start=None,
                 timestamp_end=None):
        self.httpversion = httpversion
        self.headers = headers
        """@type: ODictCaseless"""
        self.content = content

        self.timestamp_start = timestamp_start if timestamp_start is not None else utils.timestamp()
        self.timestamp_end = timestamp_end if timestamp_end is not None else utils.timestamp()

        self.flow = None  # will usually be set by the flow backref mixin
        """@type: HTTPFlow"""

    _stateobject_attributes = dict(
        httpversion=tuple,
        headers=ODictCaseless,
        content=str,
        timestamp_start=float,
        timestamp_end=float
    )

    def get_decoded_content(self):
        """
            Returns the decoded content based on the current Content-Encoding header.
            Doesn't change the message iteself or its headers.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return self.content
        return encoding.decode(ce, self.content)

    def decode(self):
        """
            Decodes content based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.

            Returns True if decoding succeeded, False otherwise.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return False
        data = encoding.decode(ce, self.content)
        if data is None:
            return False
        self.content = data
        del self.headers["content-encoding"]
        return True

    def encode(self, e):
        """
            Encodes content with the encoding e, where e is "gzip", "deflate"
            or "identity".
        """
        # FIXME: Error if there's an existing encoding header?
        self.content = encoding.encode(e, self.content)
        self.headers["content-encoding"] = [e]

    def size(self, **kwargs):
        """
            Size in bytes of a fully rendered message, including headers and
            HTTP lead-in.
        """
        hl = len(self._assemble_head(**kwargs))
        if self.content:
            return hl + len(self.content)
        else:
            return hl

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the message. Encoded content will be decoded
            before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = utils.safe_subn(pattern, repl, self.content, *args, **kwargs)
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c

    @classmethod
    def from_stream(cls, rfile, include_body=True, body_size_limit=None):
        """
        Parse an HTTP message from a file stream
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_first_line(self):
        """
        Returns the assembled request/response line
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_headers(self):
        """
        Returns the assembled headers
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_head(self):
        """
        Returns the assembled request/response line plus headers
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble(self):
        """
        Returns the assembled request/response
        """
        raise NotImplementedError  # pragma: nocover


class HTTPRequest(HTTPMessage):
    """
    An HTTP request.

    Exposes the following attributes:

        flow: Flow object the request belongs to

        headers: ODictCaseless object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        form_in: The request form which mitmproxy has received. The following values are possible:
                 - relative (GET /index.html, OPTIONS *) (covers origin form and asterisk form)
                 - absolute (GET http://example.com:80/index.html)
                 - authority-form (CONNECT example.com:443)
                 Details: http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-25#section-5.3

        form_out: The request form which mitmproxy has send out to the destination

        method: HTTP method

        scheme: URL scheme (http/https) (absolute-form only)

        host: Host portion of the URL (absolute-form and authority-form only)

        port: Destination port (absolute-form and authority-form only)

        path: Path portion of the URL (not present in authority-form)

        httpversion: HTTP version tuple

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(self, form_in, method, scheme, host, port, path, httpversion, headers,
                 content, timestamp_start=None, timestamp_end=None, form_out=None):
        assert isinstance(headers, ODictCaseless) or not headers
        HTTPMessage.__init__(self, httpversion, headers, content, timestamp_start,
                             timestamp_end)

        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.httpversion = httpversion
        self.form_out = form_out or form_in

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False
        # Is this request replayed?
        self.is_replay = False

    _stateobject_attributes = HTTPMessage._stateobject_attributes.copy()
    _stateobject_attributes.update(
        form_in=str,
        method=str,
        scheme=str,
        host=str,
        port=int,
        path=str,
        form_out=str
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None, None, None, None, None, None, None, None, None, None)
        f._load_state(state)
        return f

    def __repr__(self):
        return "<HTTPRequest: {0}>".format(self._assemble_first_line(self.form_in)[:-9])

    @classmethod
    def from_stream(cls, rfile, include_body=True, body_size_limit=None):
        """
        Parse an HTTP request from a file stream
        """
        httpversion, host, port, scheme, method, path, headers, content, timestamp_start, timestamp_end = (
            None, None, None, None, None, None, None, None, None, None)

        timestamp_start = utils.timestamp()

        if hasattr(rfile, "reset_timestamps"):
            rfile.reset_timestamps()

        request_line = get_line(rfile)

        if hasattr(rfile, "first_byte_timestamp"):  # more accurate timestamp_start
            timestamp_start = rfile.first_byte_timestamp

        request_line_parts = http.parse_init(request_line)
        if not request_line_parts:
            raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        method, path, httpversion = request_line_parts

        if path == '*' or path.startswith("/"):
            form_in = "relative"
            if not netlib.utils.isascii(path):
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        elif method.upper() == 'CONNECT':
            form_in = "authority"
            r = http.parse_init_connect(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            host, port, _ = r
            path = None
        else:
            form_in = "absolute"
            r = http.parse_init_proxy(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            _, scheme, host, port, path, _ = r

        headers = http.read_headers(rfile)
        if headers is None:
            raise http.HttpError(400, "Invalid headers")

        if include_body:
            content = http.read_http_body(rfile, headers, body_size_limit,
                                          method, None, True)
            timestamp_end = utils.timestamp()

        return HTTPRequest(form_in, method, scheme, host, port, path, httpversion, headers,
                           content, timestamp_start, timestamp_end)

    def _assemble_first_line(self, form=None):
        form = form or self.form_out

        if form == "relative":
            path = self.path if self.method != "OPTIONS" else "*"
            request_line = '%s %s HTTP/%s.%s' % \
                           (self.method, path, self.httpversion[0], self.httpversion[1])
        elif form == "authority":
            request_line = '%s %s:%s HTTP/%s.%s' % (self.method, self.host, self.port,
                                                    self.httpversion[0], self.httpversion[1])
        elif form == "absolute":
            request_line = '%s %s://%s:%s%s HTTP/%s.%s' % \
                           (self.method, self.scheme, self.host, self.port, self.path,
                            self.httpversion[0], self.httpversion[1])
        else:
            raise http.HttpError(400, "Invalid request form")
        return request_line

    def _assemble_headers(self):
        headers = self.headers.copy()
        for k in ['Proxy-Connection',
                  'Keep-Alive',
                  'Connection',
                  'Transfer-Encoding']:
            del headers[k]
        if headers["Upgrade"] == ["h2c"]:  # Suppress HTTP2 https://http2.github.io/http2-spec/index.html#discover-http
            del headers["Upgrade"]
        if not 'host' in headers:
            headers["Host"] = [utils.hostport(self.scheme,
                                              self.host or self.flow.server_conn.address.host,
                                              self.port or self.flow.server_conn.address.port)]

        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        elif 'Transfer-Encoding' in self.headers:  # content-length for e.g. chuncked transfer-encoding with no content
            headers["Content-Length"] = ["0"]

        return str(headers)

    def _assemble_head(self, form=None):
        return "%s\r\n%s\r\n" % (self._assemble_first_line(form), self._assemble_headers())

    def _assemble(self, form=None):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.

            Raises an Exception if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            raise proxy.ProxyError(502, "Cannot assemble flow with CONTENT_MISSING")
        head = self._assemble_head(form)
        if self.content:
            return head + self.content
        else:
            return head

    def __hash__(self):
        return id(self)

    def anticache(self):
        """
            Modifies this request to remove headers that might produce a cached
            response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            "if-modified-since",
            "if-none-match",
        ]
        for i in delheaders:
            del self.headers[i]

    def anticomp(self):
        """
            Modifies this request to remove headers that will compress the
            resource's data.
        """
        self.headers["accept-encoding"] = ["identity"]

    def constrain_encoding(self):
        """
            Limits the permissible Accept-Encoding values, based on what we can
            decode appropriately.
        """
        if self.headers["accept-encoding"]:
            self.headers["accept-encoding"] = [', '.join(
                e for e in encoding.ENCODINGS if e in self.headers["accept-encoding"][0]
            )]

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.content and self.headers.in_any("content-type", HDR_FORM_URLENCODED, True):
            return ODict(utils.urldecode(self.content))
        return ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        # FIXME: If there's an existing content-type header indicating a
        # url-encoded form, leave it alone.
        self.headers["Content-Type"] = [HDR_FORM_URLENCODED]
        self.content = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urlparse.urlparse(self.get_url())
        return [urllib.unquote(i) for i in path.split("/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.quote(i, safe="") for i in lst]
        path = "/" + "/".join(lst)
        scheme, netloc, _, params, query, fragment = urlparse.urlparse(self.get_url())
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_query(self):
        """
            Gets the request query string. Returns an ODict object.
        """
        _, _, _, _, query, _ = urlparse.urlparse(self.get_url())
        if query:
            return ODict(utils.urldecode(query))
        return ODict([])

    def set_query(self, odict):
        """
            Takes an ODict object, and sets the request query string.
        """
        scheme, netloc, path, params, _, fragment = urlparse.urlparse(self.get_url())
        query = utils.urlencode(odict.lst)
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_host(self, hostheader=False):
        """
            Heuristic to get the host of the request.

            Note that get_host() does not always return the TCP destination of the request,
            e.g. on a transparently intercepted request to an unrelated HTTP proxy.

            If hostheader is set to True, the Host: header will be used as additional (and preferred) data source.
            This is handy in transparent mode, where only the ip of the destination is known, but not the
            resolved name. This is disabled by default, as an attacker may spoof the host header to confuse an analyst.
        """
        host = None
        if hostheader:
            host = self.headers.get_first("host")
        if not host:
            if self.host:
                host = self.host
            else:
                for s in self.flow.server_conn.state:
                    if s[0] == "http" and s[1]["state"] == "connect":
                        host = s[1]["host"]
                        break
                if not host:
                    host = self.flow.server_conn.address.host
        host = host.encode("idna")
        return host

    def get_scheme(self):
        """
        Returns the request port, either from the request itself or from the flow's server connection
        """
        if self.scheme:
            return self.scheme
        if self.form_out == "authority":  # On SSLed connections, the original CONNECT request is still unencrypted.
            return "http"
        return "https" if self.flow.server_conn.ssl_established else "http"

    def get_port(self):
        """
        Returns the request port, either from the request itself or from the flow's server connection
        """
        if self.port:
            return self.port
        for s in self.flow.server_conn.state:
            if s[0] == "http" and s[1].get("state") == "connect":
                return s[1]["port"]
        return self.flow.server_conn.address.port

    def get_url(self, hostheader=False):
        """
            Returns a URL string, constructed from the Request's URL components.

            If hostheader is True, we use the value specified in the request
            Host header to construct the URL.
        """
        if self.form_out == "authority":  # upstream proxy mode
            return "%s:%s" % (self.get_host(hostheader), self.get_port())
        return utils.unparse_url(self.get_scheme(),
                                 self.get_host(hostheader),
                                 self.get_port(),
                                 self.path).encode('ascii')

    def set_url(self, url):
        """
            Parses a URL specification, and updates the Request's information
            accordingly.

            Returns False if the URL was invalid, True if the request succeeded.
        """
        parts = http.parse_url(url)
        if not parts:
            return False
        scheme, host, port, path = parts
        is_ssl = (True if scheme == "https" else False)

        self.path = path

        if host != self.get_host() or port != self.get_port():
            if self.flow.live:
                self.flow.live.change_server((host, port), ssl=is_ssl)
            else:
                # There's not live server connection, we're just changing the attributes here.
                self.flow.server_conn = ServerConnection((host, port),
                                                         proxy.AddressPriority.MANUALLY_CHANGED)
                self.flow.server_conn.ssl_established = is_ssl

        # If this is an absolute request, replace the attributes on the request object as well.
        if self.host:
            self.host = host
        if self.port:
            self.port = port
        if self.scheme:
            self.scheme = scheme

        return True

    def get_cookies(self):
        cookie_headers = self.headers.get("cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookies.extend((pair[0], (pair[2], {})) for pair in pairs)
        return dict(cookies)

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in the headers, the request path
            and the body of the request. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = HTTPMessage.replace(self, pattern, repl, *args, **kwargs)
        self.path, pc = utils.safe_subn(pattern, repl, self.path, *args, **kwargs)
        c += pc
        return c


class HTTPResponse(HTTPMessage):
    """
    An HTTP response.

    Exposes the following attributes:

        flow: Flow object the request belongs to

        code: HTTP response code

        msg: HTTP response message

        headers: ODict object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        httpversion: HTTP version tuple

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(self, httpversion, code, msg, headers, content, timestamp_start=None,
                 timestamp_end=None):
        assert isinstance(headers, ODictCaseless) or headers is None
        HTTPMessage.__init__(self, httpversion, headers, content, timestamp_start,
                             timestamp_end)

        self.code = code
        self.msg = msg

        # Is this request replayed?
        self.is_replay = False
        self.stream = False

    _stateobject_attributes = HTTPMessage._stateobject_attributes.copy()
    _stateobject_attributes.update(
        code=int,
        msg=str
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None, None, None, None)
        f._load_state(state)
        return f

    def __repr__(self):
        return "<HTTPResponse: {code} {msg} ({contenttype}, {size})>".format(
            code=self.code,
            msg=self.msg,
            contenttype=self.headers.get_first("content-type", "?"),
            size=utils.pretty_size(len(self.content))
        )

    @classmethod
    def from_stream(cls, rfile, request_method, include_body=True, body_size_limit=None):
        """
        Parse an HTTP response from a file stream
        """

        timestamp_start = utils.timestamp()

        if hasattr(rfile, "reset_timestamps"):
            rfile.reset_timestamps()

        httpversion, code, msg, headers, content = http.read_response(
            rfile,
            request_method,
            body_size_limit,
            include_body=include_body)

        if hasattr(rfile, "first_byte_timestamp"):  # more accurate timestamp_start
            timestamp_start = rfile.first_byte_timestamp

        timestamp_end = utils.timestamp()
        return HTTPResponse(httpversion, code, msg, headers, content, timestamp_start,
                            timestamp_end)

    def _assemble_first_line(self):
        return 'HTTP/%s.%s %s %s' % \
               (self.httpversion[0], self.httpversion[1], self.code, self.msg)

    def _assemble_headers(self, preserve_transfer_encoding=False):
        headers = self.headers.copy()
        for k in ['Proxy-Connection',
                  'Alternate-Protocol',
                  'Alt-Svc']:
            del headers[k]
        if not preserve_transfer_encoding:
            del headers['Transfer-Encoding']

        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        elif not preserve_transfer_encoding and 'Transfer-Encoding' in self.headers:  # add content-length for chuncked transfer-encoding with no content
            headers["Content-Length"] = ["0"]

        return str(headers)

    def _assemble_head(self, preserve_transfer_encoding=False):
        return '%s\r\n%s\r\n' % (
            self._assemble_first_line(), self._assemble_headers(preserve_transfer_encoding=preserve_transfer_encoding))

    def _assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.

            Raises an Exception if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            raise proxy.ProxyError(502, "Cannot assemble flow with CONTENT_MISSING")
        head = self._assemble_head()
        if self.content:
            return head + self.content
        else:
            return head

    def _refresh_cookie(self, c, delta):
        """
            Takes a cookie string c and a time delta in seconds, and returns
            a refreshed cookie string.
        """
        c = Cookie.SimpleCookie(str(c))
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
        return c.output(header="").strip()

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
                d = parsedate_tz(self.headers[i][0])
                if d:
                    new = mktime_tz(d) + delta
                    self.headers[i] = [formatdate(new)]
        c = []
        for i in self.headers["set-cookie"]:
            c.append(self._refresh_cookie(i, delta))
        if c:
            self.headers["set-cookie"] = c

    def get_cookies(self):
        cookie_headers = self.headers.get("set-cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookie_name = pairs[0][0]  # the key of the first key/value pairs
            cookie_value = pairs[0][2]  # the value of the first key/value pairs
            cookie_parameters = {key.strip().lower(): value.strip() for key, sep, value in
                                 pairs[1:]}
            cookies.append((cookie_name, (cookie_value, cookie_parameters)))
        return dict(cookies)


class HTTPFlow(Flow):
    """
    A Flow is a collection of objects representing a single HTTP
    transaction. The main attributes are:

        request: HTTPRequest object
        response: HTTPResponse object
        error: Error object

    Note that it's possible for a Flow to have both a response and an error
    object. This might happen, for instance, when a response was received
    from the server, but there was an error sending it back to the client.

    The following additional attributes are exposed:

        intercepting: Is this flow currently being intercepted?
        live: Does this flow have a live client connection?
    """

    def __init__(self, client_conn, server_conn, live=None):
        super(HTTPFlow, self).__init__("http", client_conn, server_conn, live)
        self.request = None
        """@type: HTTPRequest"""
        self.response = None
        """@type: HTTPResponse"""

        self.intercepting = False  # FIXME: Should that rather be an attribute of Flow?

    _backrefattr = Flow._backrefattr + ("request", "response")

    _stateobject_attributes = Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        request=HTTPRequest,
        response=HTTPResponse
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None)
        f._load_state(state)
        return f

    def __repr__(self):
        s = "<HTTPFlow"
        for a in ("request", "response", "error", "client_conn", "server_conn"):
            if getattr(self, a, False):
                s += "\r\n  %s = {flow.%s}" % (a,a)
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

    def kill(self, master):
        """
            Kill this request.
        """
        self.error = Error("Connection killed")
        self.error.reply = controller.DummyReply()
        if self.request and not self.request.reply.acked:
            self.request.reply(KILL)
        elif self.response and not self.response.reply.acked:
            self.response.reply(KILL)
        master.handle_error(self.error)
        self.intercepting = False

    def intercept(self):
        """
            Intercept this Flow. Processing will stop until accept_intercept is
            called.
        """
        self.intercepting = True

    def accept_intercept(self):
        """
            Continue with the flow - called after an intercept().
        """
        if self.request:
            if not self.request.reply.acked:
                self.request.reply()
            elif self.response and not self.response.reply.acked:
                self.response.reply()
            self.intercepting = False

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both request and response of the
            flow. Encoded content will be decoded before replacement, and
            re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = self.request.replace(pattern, repl, *args, **kwargs)
        if self.response:
            c += self.response.replace(pattern, repl, *args, **kwargs)
        return c


class HttpAuthenticationError(Exception):
    def __init__(self, auth_headers=None):
        super(HttpAuthenticationError, self).__init__("Proxy Authentication Required")
        self.headers = auth_headers
        self.code = 407

    def __repr__(self):
        return "Proxy Authentication Required"


class HTTPHandler(ProtocolHandler):
    def __init__(self, c):
        super(HTTPHandler, self).__init__(c)
        self.expected_form_in = c.config.http_form_in
        self.expected_form_out = c.config.http_form_out
        self.skip_authentication = False

    def handle_messages(self):
        while self.handle_flow():
            pass
        self.c.close = True

    def get_response_from_server(self, request, include_body=True):
        self.c.establish_server_connection()
        request_raw = request._assemble()

        for i in range(2):
            try:
                self.c.server_conn.send(request_raw)
                res = HTTPResponse.from_stream(self.c.server_conn.rfile, request.method,
                                               body_size_limit=self.c.config.body_size_limit, include_body=include_body)
                return res
            except (tcp.NetLibDisconnect, http.HttpErrorConnClosed), v:
                self.c.log("error in server communication: %s" % str(v), level="debug")
                if i < 1:
                    # In any case, we try to reconnect at least once.
                    # This is necessary because it might be possible that we already initiated an upstream connection
                    # after clientconnect that has already been expired, e.g consider the following event log:
                    # > clientconnect (transparent mode destination known)
                    # > serverconnect
                    # > read n% of large request
                    # > server detects timeout, disconnects
                    # > read (100-n)% of large request
                    # > send large request upstream
                    self.c.server_reconnect()
                else:
                    raise v

    def handle_flow(self):
        flow = HTTPFlow(self.c.client_conn, self.c.server_conn, self.live)
        try:
            req = HTTPRequest.from_stream(self.c.client_conn.rfile,
                                          body_size_limit=self.c.config.body_size_limit)
            self.c.log("request", "debug", [req._assemble_first_line(req.form_in)])
            send_request_upstream = self.process_request(flow, req)
            if not send_request_upstream:
                return True

            # Be careful NOT to assign the request to the flow before
            # process_request completes. This is because the call can raise an
            # exception. If the request object is already attached, this results
            # in an Error object that has an attached request that has not been
            # sent through to the Master.
            flow.request = req
            request_reply = self.c.channel.ask("request", flow.request)
            self.determine_server_address(flow, flow.request)
            flow.server_conn = self.c.server_conn  # Update server_conn attribute on the flow

            if request_reply is None or request_reply == KILL:
                return False

            if isinstance(request_reply, HTTPResponse):
                flow.response = request_reply
            else:

                # read initially in "stream" mode, so we can get the headers separately
                flow.response = self.get_response_from_server(flow.request, include_body=False)

                # call the appropriate script hook - this is an opportunity for an inline script to set flow.stream = True
                self.c.channel.ask("responseheaders", flow.response)

                # now get the rest of the request body, if body still needs to be read but not streaming this response
                if flow.response.stream:
                    flow.response.content = CONTENT_MISSING
                else:
                    flow.response.content = http.read_http_body(self.c.server_conn.rfile, flow.response.headers,
                                                                self.c.config.body_size_limit,
                                                                flow.request.method, flow.response.code, False)

            # no further manipulation of self.c.server_conn beyond this point
            # we can safely set it as the final attribute value here.
            flow.server_conn = self.c.server_conn

            self.c.log("response", "debug", [flow.response._assemble_first_line()])
            response_reply = self.c.channel.ask("response", flow.response)
            if response_reply is None or response_reply == KILL:
                return False

            if not flow.response.stream:
                # no streaming:
                # we already received the full response from the server and can send it to the client straight away.
                self.c.client_conn.send(flow.response._assemble())
            else:
                # streaming:
                # First send the body and then transfer the response incrementally:
                h = flow.response._assemble_head(preserve_transfer_encoding=True)
                self.c.client_conn.send(h)
                for chunk in http.read_http_body_chunked(self.c.server_conn.rfile,
                                                         flow.response.headers,
                                                         self.c.config.body_size_limit, flow.request.method,
                                                         flow.response.code, False, 4096):
                    for part in chunk:
                        self.c.client_conn.wfile.write(part)
                    self.c.client_conn.wfile.flush()
                flow.response.timestamp_end = utils.timestamp()

            flow.timestamp_end = utils.timestamp()

            close_connection = (
                http.connection_close(flow.request.httpversion, flow.request.headers) or
                http.connection_close(flow.response.httpversion, flow.response.headers) or
                http.expected_http_body_size(flow.response.headers, False, flow.request.method,
                                             flow.response.code) == -1)
            if close_connection:
                if flow.request.form_in == "authority" and flow.response.code == 200:
                    # Workaround for https://github.com/mitmproxy/mitmproxy/issues/313:
                    # Some proxies (e.g. Charles) send a CONNECT response with HTTP/1.0 and no Content-Length header
                    pass
                else:
                    return False

            if flow.request.form_in == "authority" and flow.response.code == 200:
                # TODO: Eventually add headers (space/usefulness tradeoff)
                # Make sure to add state info before the actual upgrade happens.
                # During the upgrade, we may receive an SNI indication from the client,
                # which resets the upstream connection. If this is the case, we must
                # already re-issue the CONNECT request at this point.
                self.c.server_conn.state.append(("http", {"state": "connect",
                                                          "host": flow.request.host,
                                                          "port": flow.request.port}))
                self.ssl_upgrade()

            # If the user has changed the target server on this connection,
            # restore the original target server
            flow.live.restore_server()
            flow.live = None

            return True
        except (HttpAuthenticationError, http.HttpError, proxy.ProxyError, tcp.NetLibError), e:
            self.handle_error(e, flow)
        return False

    def handle_server_reconnect(self, state):
        if state["state"] == "connect":
            send_connect_request(self.c.server_conn, state["host"], state["port"])
        else:  # pragma: nocover
            raise RuntimeError("Unknown State: %s" % state["state"])

    def handle_error(self, error, flow=None):

        message = repr(error)
        code = getattr(error, "code", 502)
        headers = getattr(error, "headers", None)

        if "tlsv1 alert unknown ca" in message:
            message = message + " \nThe client does not trust the proxy's certificate."

        self.c.log("error: %s" % message, level="info")

        if flow:
            flow.error = Error(message)
            # FIXME: no flows without request or with both request and response at the moement.
            if flow.request and not flow.response:
                self.c.channel.ask("error", flow.error)
        else:
            pass  # FIXME: Do we want to persist errors without flows?

        try:
            self.send_error(code, message, headers)
        except:
            pass

    def send_error(self, code, message, headers):
        response = http_status.RESPONSES.get(code, "Unknown")
        html_content = '<html><head>\n<title>%d %s</title>\n</head>\n<body>\n%s\n</body>\n</html>' % \
                       (code, response, message)
        self.c.client_conn.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
        self.c.client_conn.wfile.write("Server: %s\r\n" % self.c.server_version)
        self.c.client_conn.wfile.write("Content-type: text/html\r\n")
        self.c.client_conn.wfile.write("Content-Length: %d\r\n" % len(html_content))
        if headers:
            for key, value in headers.items():
                self.c.client_conn.wfile.write("%s: %s\r\n" % (key, value))
        self.c.client_conn.wfile.write("Connection: close\r\n")
        self.c.client_conn.wfile.write("\r\n")
        self.c.client_conn.wfile.write(html_content)
        self.c.client_conn.wfile.flush()

    def ssl_upgrade(self):
        """
        Upgrade the connection to SSL after an authority (CONNECT) request has been made.
        """
        self.c.log("Received CONNECT request. Upgrading to SSL...", "debug")
        self.expected_form_in = "relative"
        self.expected_form_out = "relative"
        self.c.establish_ssl(server=True, client=True)
        self.c.log("Upgrade to SSL completed.", "debug")

    def process_request(self, flow, request):

        if not self.skip_authentication:
            self.authenticate(request)

        if request.form_in == "authority":
            if self.c.client_conn.ssl_established:
                raise http.HttpError(400, "Must not CONNECT on already encrypted connection")

            if self.expected_form_in == "absolute":
                if not self.c.config.get_upstream_server:
                    self.c.set_server_address((request.host, request.port),
                                              proxy.AddressPriority.FROM_PROTOCOL)
                    self.c.establish_server_connection()
                    flow.server_conn = self.c.server_conn  # Update server_conn attribute on the flow
                    self.c.client_conn.send(
                        'HTTP/1.1 200 Connection established\r\n' +
                        'Content-Length: 0\r\n' +
                        ('Proxy-agent: %s\r\n' % self.c.server_version) +
                        '\r\n'
                    )

                    self.ssl_upgrade()
                    self.skip_authentication = True
                    return False
                else:
                    return True
        elif request.form_in == self.expected_form_in:
            if request.form_in == "absolute":
                if request.scheme != "http":
                    raise http.HttpError(400, "Invalid request scheme: %s" % request.scheme)
                self.determine_server_address(flow, request)
            request.form_out = self.expected_form_out
            return True

        raise http.HttpError(400, "Invalid HTTP request form (expected: %s, got: %s)" %
                             (self.expected_form_in, request.form_in))

    def determine_server_address(self, flow, request):
        if request.form_in == "absolute":
            self.c.set_server_address((request.host, request.port),
                                      proxy.AddressPriority.FROM_PROTOCOL)
            flow.server_conn = self.c.server_conn  # Update server_conn attribute on the flow

    def authenticate(self, request):
        if self.c.config.authenticator:
            if self.c.config.authenticator.authenticate(request.headers):
                self.c.config.authenticator.clean(request.headers)
            else:
                raise HttpAuthenticationError(
                    self.c.config.authenticator.auth_challenge_headers())
        return request.headers


class RequestReplayThread(threading.Thread):
    name = "RequestReplayThread"

    def __init__(self, config, flow, masterq, should_exit):
        self.config, self.flow, self.channel = config, flow, controller.Channel(masterq, should_exit)
        threading.Thread.__init__(self)

    def run(self):
        try:
            r = self.flow.request
            form_out_backup = r.form_out

            r.form_out = self.config.http_form_out
            server_address, server_ssl = False, False
            if self.config.get_upstream_server:
                try:
                    upstream_info = self.config.get_upstream_server(self.flow.client_conn)
                    server_ssl = upstream_info[1]
                    server_address = upstream_info[2:]
                except proxy.ProxyError:  # this will fail in transparent mode
                    pass
            if not server_address:
                server_address = (r.get_host(), r.get_port())

            server = ServerConnection(server_address, None)
            server.connect()

            if server_ssl or r.get_scheme() == "https":
                if self.config.http_form_out == "absolute":
                    send_connect_request(server, r.get_host(), r.get_port())
                    r.form_out = "relative"
                server.establish_ssl(self.config.clientcerts,
                                     self.flow.server_conn.sni)
            server.send(r._assemble())
            self.flow.response = HTTPResponse.from_stream(server.rfile, r.method,
                                                          body_size_limit=self.config.body_size_limit)
            self.channel.ask("response", self.flow.response)
        except (proxy.ProxyError, http.HttpError, tcp.NetLibError), v:
            self.flow.error = Error(repr(v))
            self.channel.ask("error", self.flow.error)
        finally:
            r.form_out = form_out_backup