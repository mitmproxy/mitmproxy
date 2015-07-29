from __future__ import absolute_import
import Cookie
import copy
import threading
import time
import urllib
import urlparse
from email.utils import parsedate_tz, formatdate, mktime_tz

import netlib
from netlib import http, tcp, odict, utils
from netlib.http import cookies, semantics, http1

from .tcp import TCPHandler
from .primitives import KILL, ProtocolHandler, Flow, Error
from ..proxy.connection import ServerConnection
from .. import encoding, utils, controller, stateobject, proxy


HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
HDR_FORM_MULTIPART = "multipart/form-data"
CONTENT_MISSING = 0


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


class MessageMixin(stateobject.StateObject):
    _stateobject_attributes = dict(
        httpversion=tuple,
        headers=odict.ODictCaseless,
        body=str,
        timestamp_start=float,
        timestamp_end=float
    )
    _stateobject_long_attributes = {"body"}

    def get_state(self, short=False):
        ret = super(MessageMixin, self).get_state(short)
        if short:
            if self.body:
                ret["contentLength"] = len(self.body)
            elif self.body == CONTENT_MISSING:
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
        ce = self.headers.get_first("content-encoding")
        if not self.body or ce not in encoding.ENCODINGS:
            return self.body
        return encoding.decode(ce, self.body)

    def decode(self):
        """
            Decodes body based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.

            Returns True if decoding succeeded, False otherwise.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.body or ce not in encoding.ENCODINGS:
            return False
        data = encoding.decode(ce, self.body)
        if data is None:
            return False
        self.body = data
        del self.headers["content-encoding"]
        return True

    def encode(self, e):
        """
            Encodes body with the encoding e, where e is "gzip", "deflate"
            or "identity".
        """
        # FIXME: Error if there's an existing encoding header?
        self.body = encoding.encode(e, self.body)
        self.headers["content-encoding"] = [e]

    def copy(self):
        c = copy.copy(self)
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
            self.body, c = utils.safe_subn(
                pattern, repl, self.body, *args, **kwargs
            )
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c


class HTTPRequest(MessageMixin, semantics.Request):
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

        httpversion: HTTP version tuple, e.g. (1,1)

        headers: odict.ODictCaseless object

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
        form_in,
        method,
        scheme,
        host,
        port,
        path,
        httpversion,
        headers,
        body,
        timestamp_start=None,
        timestamp_end=None,
        form_out=None,
    ):
        semantics.Request.__init__(
            self,
            form_in,
            method,
            scheme,
            host,
            port,
            path,
            httpversion,
            headers,
            body,
            timestamp_start,
            timestamp_end,
        )
        self.form_out = form_out or form_in

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False

        # Is this request replayed?
        self.is_replay = False

    _stateobject_attributes = MessageMixin._stateobject_attributes.copy()
    _stateobject_attributes.update(
        form_in=str,
        method=str,
        scheme=str,
        host=str,
        port=int,
        path=str,
        form_out=str,
        is_replay=bool
    )

    # This list is adopted legacy code.
    # We probably don't need to strip off keep-alive.
    _headers_to_strip_off = ['Proxy-Connection',
                             'Keep-Alive',
                             'Connection',
                             'Transfer-Encoding',
                             'Upgrade']

    @classmethod
    def from_state(cls, state):
        f = cls(
            None,
            None,
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

    def __repr__(self):
        return "<HTTPRequest: {0}>".format(
            # just for visualisation purposes we use HTTP/1 protocol here
            http.http1.HTTP1Protocol._assemble_request_first_line(self)[:-9]
        )

    @classmethod
    def from_protocol(
            self,
            protocol,
            include_body=True,
            body_size_limit=None,
    ):
        req = protocol.read_request(
            include_body = include_body,
            body_size_limit = body_size_limit,
        )

        return HTTPRequest(
            req.form_in,
            req.method,
            req.scheme,
            req.host,
            req.port,
            req.path,
            req.httpversion,
            req.headers,
            req.body,
            req.timestamp_start,
            req.timestamp_end,
        )


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
            self.headers["accept-encoding"] = [
                ', '.join(
                    e for e in encoding.ENCODINGS if e in self.headers["accept-encoding"][0])]

    def update_host_header(self):
        """
            Update the host header to reflect the current target.
        """
        self.headers["Host"] = [self.host]

    def get_form(self):
        """
            Retrieves the URL-encoded or multipart form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body:
            if self.headers.in_any("content-type", HDR_FORM_URLENCODED, True):
                return self.get_form_urlencoded()
            elif self.headers.in_any("content-type", HDR_FORM_MULTIPART, True):
                return self.get_form_multipart()
        return odict.ODict([])

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body and self.headers.in_any(
                "content-type",
                HDR_FORM_URLENCODED,
                True):
            return odict.ODict(utils.urldecode(self.body))
        return odict.ODict([])

    def get_form_multipart(self):
        if self.body and self.headers.in_any(
                "content-type",
                HDR_FORM_MULTIPART,
                True):
            return odict.ODict(
                utils.multipartdecode(
                    self.headers,
                    self.body))
        return odict.ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        # FIXME: If there's an existing content-type header indicating a
        # url-encoded form, leave it alone.
        self.headers["Content-Type"] = [HDR_FORM_URLENCODED]
        self.body = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urlparse.urlparse(self.url)
        return [urllib.unquote(i) for i in path.split("/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.quote(i, safe="") for i in lst]
        path = "/" + "/".join(lst)
        scheme, netloc, _, params, query, fragment = urlparse.urlparse(self.url)
        self.url = urlparse.urlunparse(
            [scheme, netloc, path, params, query, fragment]
        )

    def get_query(self):
        """
            Gets the request query string. Returns an ODict object.
        """
        _, _, _, _, query, _ = urlparse.urlparse(self.url)
        if query:
            return odict.ODict(utils.urldecode(query))
        return odict.ODict([])

    def set_query(self, odict):
        """
            Takes an ODict object, and sets the request query string.
        """
        scheme, netloc, path, params, _, fragment = urlparse.urlparse(self.url)
        query = utils.urlencode(odict.lst)
        self.url = urlparse.urlunparse(
            [scheme, netloc, path, params, query, fragment]
        )

    def pretty_host(self, hostheader):
        """
            Heuristic to get the host of the request.

            Note that pretty_host() does not always return the TCP destination
            of the request, e.g. if an upstream proxy is in place

            If hostheader is set to True, the Host: header will be used as
            additional (and preferred) data source. This is handy in
            transparent mode, where only the IO of the destination is known,
            but not the resolved name. This is disabled by default, as an
            attacker may spoof the host header to confuse an analyst.
        """
        host = None
        if hostheader:
            host = self.headers.get_first("host")
        if not host:
            host = self.host
        if host:
            try:
                return host.encode("idna")
            except ValueError:
                return host
        else:
            return None

    def pretty_url(self, hostheader):
        if self.form_out == "authority":  # upstream proxy mode
            return "%s:%s" % (self.pretty_host(hostheader), self.port)
        return utils.unparse_url(self.scheme,
                                 self.pretty_host(hostheader),
                                 self.port,
                                 self.path).encode('ascii')

    @property
    def url(self):
        """
            Returns a URL string, constructed from the Request's URL components.
        """
        return utils.unparse_url(
            self.scheme,
            self.host,
            self.port,
            self.path
        ).encode('ascii')

    @url.setter
    def url(self, url):
        """
            Parses a URL specification, and updates the Request's information
            accordingly.

            Returns False if the URL was invalid, True if the request succeeded.
        """
        parts = http.parse_url(url)
        if not parts:
            raise ValueError("Invalid URL: %s" % url)
        self.scheme, self.host, self.port, self.path = parts

    def get_cookies(self):
        """

            Returns a possibly empty netlib.odict.ODict object.
        """
        ret = odict.ODict()
        for i in self.headers["cookie"]:
            ret.extend(cookies.parse_cookie_header(i))
        return ret

    def set_cookies(self, odict):
        """
            Takes an netlib.odict.ODict object. Over-writes any existing Cookie
            headers.
        """
        v = cookies.format_cookie_header(odict)
        self.headers["Cookie"] = [v]

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


class HTTPResponse(MessageMixin, semantics.Response):
    """
    An HTTP response.

    Exposes the following attributes:

        httpversion: HTTP version tuple, e.g. (1, 0), (1, 1), or (2, 0)

        status_code: HTTP response status code

        msg: HTTP response message

        headers: ODict Caseless object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(
            self,
            httpversion,
            status_code,
            msg,
            headers,
            body,
            timestamp_start=None,
            timestamp_end=None,
    ):
        semantics.Response.__init__(
            self,
            httpversion,
            status_code,
            msg,
            headers,
            body,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        # Is this request replayed?
        self.is_replay = False
        self.stream = False

    _stateobject_attributes = MessageMixin._stateobject_attributes.copy()
    _stateobject_attributes.update(
        code=int,
        msg=str
    )

    _headers_to_strip_off = ['Proxy-Connection',
                             'Alternate-Protocol',
                             'Alt-Svc']


    @classmethod
    def from_state(cls, state):
        f = cls(None, None, None, None, None)
        f.load_state(state)
        return f

    def __repr__(self):
        if self.body:
            size = netlib.utils.pretty_size(len(self.body))
        else:
            size = "content missing"
        return "<HTTPResponse: {status_code} {msg} ({contenttype}, {size})>".format(
            status_code=self.status_code,
            msg=self.msg,
            contenttype=self.headers.get_first(
                "content-type", "unknown content type"
            ),
            size=size
        )

    @classmethod
    def from_protocol(
            self,
            protocol,
            request_method,
            include_body=True,
            body_size_limit=None
    ):
        resp = protocol.read_response(
            request_method,
            body_size_limit,
            include_body=include_body
        )

        return HTTPResponse(
            resp.httpversion,
            resp.status_code,
            resp.msg,
            resp.headers,
            resp.body,
            resp.timestamp_start,
            resp.timestamp_end,
        )

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
        """
            Get the contents of all Set-Cookie headers.

            Returns a possibly empty ODict, where keys are cookie name strings,
            and values are [value, attr] lists. Value is a string, and attr is
            an ODictCaseless containing cookie attributes. Within attrs, unary
            attributes (e.g. HTTPOnly) are indicated by a Null value.
        """
        ret = []
        for header in self.headers["set-cookie"]:
            v = http.cookies.parse_set_cookie_header(header)
            if v:
                name, value, attrs = v
                ret.append([name, [value, attrs]])
        return odict.ODict(ret)

    def set_cookies(self, odict):
        """
            Set the Set-Cookie headers on this response, over-writing existing
            headers.

            Accepts an ODict of the same format as that returned by get_cookies.
        """
        values = []
        for i in odict.lst:
            values.append(
                http.cookies.format_set_cookie_header(
                    i[0],
                    i[1][0],
                    i[1][1]
                )
            )
        self.headers["Set-Cookie"] = values
