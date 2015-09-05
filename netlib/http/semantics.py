from __future__ import (absolute_import, print_function, division)
import UserDict
import urllib
import urlparse

from .. import utils, odict
from . import cookies, exceptions
from netlib import utils, encoding

HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
HDR_FORM_MULTIPART = "multipart/form-data"

CONTENT_MISSING = 0


class Headers(UserDict.DictMixin):
    """
    Header class which allows both convenient access to individual headers as well as
    direct access to the underlying raw data. Provides a full dictionary interface.

    Example:

    .. code-block:: python

        # Create header from a list of (header_name, header_value) tuples
        >>> h = Headers([
                ["Host","example.com"],
                ["Accept","text/html"],
                ["accept","application/xml"]
            ])

        # Headers mostly behave like a normal dict.
        >>> h["Host"]
        "example.com"

        # HTTP Headers are case insensitive
        >>> h["host"]
        "example.com"

        # Multiple headers are folded into a single header as per RFC7230
        >>> h["Accept"]
        "text/html, application/xml"

        # Setting a header removes all existing headers with the same name.
        >>> h["Accept"] = "application/text"
        >>> h["Accept"]
        "application/text"

        # str(h) returns a HTTP1 header block.
        >>> print(h)
        Host: example.com
        Accept: application/text

        # For full control, the raw header fields can be accessed
        >>> h.fields

        # Headers can also be crated from keyword arguments
        >>> h = Headers(host="example.com", content_type="application/xml")

    Caveats:
        For use with the "Set-Cookie" header, see :py:meth:`get_all`.
    """

    def __init__(self, fields=None, **headers):
        """
        Args:
            fields: (optional) list of ``(name, value)`` header tuples, e.g. ``[("Host","example.com")]``
            **headers: Additional headers to set. Will overwrite existing values from `fields`.
                For convenience, underscores in header names will be transformed to dashes -
                this behaviour does not extend to other methods.
                If ``**headers`` contains multiple keys that have equal ``.lower()`` s,
                the behavior is undefined.
        """
        self.fields = fields or []

        # content_type -> content-type
        headers = {
            name.replace("_", "-"): value
            for name, value in headers.iteritems()
            }
        self.update(headers)

    def __str__(self):
        return "\r\n".join(": ".join(field) for field in self.fields)

    def __getitem__(self, name):
        values = self.get_all(name)
        if not values:
            raise KeyError(name)
        else:
            return ", ".join(values)

    def __setitem__(self, name, value):
        idx = self._index(name)

        # To please the human eye, we insert at the same position the first existing header occured.
        if idx is not None:
            del self[name]
            self.fields.insert(idx, [name, value])
        else:
            self.fields.append([name, value])

    def __delitem__(self, name):
        if name not in self:
            raise KeyError(name)
        name = name.lower()
        self.fields = [
            field for field in self.fields
            if name != field[0].lower()
            ]

    def _index(self, name):
        name = name.lower()
        for i, field in enumerate(self.fields):
            if field[0].lower() == name:
                return i
        return None

    def keys(self):
        seen = set()
        names = []
        for name, _ in self.fields:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                names.append(name)
        return names

    def __eq__(self, other):
        if isinstance(other, Headers):
            return self.fields == other.fields
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_all(self, name, default=None):
        """
        Like :py:meth:`get`, but does not fold multiple headers into a single one.
        This is useful for Set-Cookie headers, which do not support folding.

        See also: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        name = name.lower()
        values = [value for n, value in self.fields if n.lower() == name]
        return values or default

    def set_all(self, name, values):
        """
        Explicitly set multiple headers for the given key.
        See: :py:meth:`get_all`
        """
        if name in self:
            del self[name]
        self.fields.extend(
            [name, value] for value in values
        )

    # Implement the StateObject protocol from mitmproxy
    def get_state(self, short=False):
        return tuple(tuple(field) for field in self.fields)

    def load_state(self, state):
        self.fields = [list(field) for field in state]

    @classmethod
    def from_state(cls, state):
        return cls([list(field) for field in state])


class ProtocolMixin(object):
    def read_request(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def read_response(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def assemble(self, message):
        if isinstance(message, Request):
            return self.assemble_request(message)
        elif isinstance(message, Response):
            return self.assemble_response(message)
        else:
            raise ValueError("HTTP message not supported.")

    def assemble_request(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def assemble_response(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError


class Request(object):
    # This list is adopted legacy code.
    # We probably don't need to strip off keep-alive.
    _headers_to_strip_off = [
        'Proxy-Connection',
        'Keep-Alive',
        'Connection',
        'Transfer-Encoding',
        'Upgrade',
    ]

    def __init__(
        self,
        form_in,
        method,
        scheme,
        host,
        port,
        path,
        httpversion,
        headers=None,
        body=None,
        timestamp_start=None,
        timestamp_end=None,
        form_out=None
    ):
        if not headers:
            headers = odict.ODictCaseless()
        assert isinstance(headers, odict.ODictCaseless)

        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.httpversion = httpversion
        self.headers = headers
        self.body = body
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end
        self.form_out = form_out or form_in

    def __eq__(self, other):
        try:
            self_d = [self.__dict__[k] for k in self.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            other_d = [other.__dict__[k] for k in other.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            return self_d == other_d
        except:
            return False

    def __repr__(self):
        # return "Request(%s - %s, %s)" % (self.method, self.host, self.path)

        return "<HTTPRequest: {0}>".format(
            self.legacy_first_line()[:-9]
        )

    def legacy_first_line(self, form=None):
        if form is None:
            form = self.form_out
        if form == "relative":
            return '%s %s HTTP/%s.%s' % (
                self.method,
                self.path,
                self.httpversion[0],
                self.httpversion[1],
            )
        elif form == "authority":
            return '%s %s:%s HTTP/%s.%s' % (
                self.method,
                self.host,
                self.port,
                self.httpversion[0],
                self.httpversion[1],
            )
        elif form == "absolute":
            return '%s %s://%s:%s%s HTTP/%s.%s' % (
                self.method,
                self.scheme,
                self.host,
                self.port,
                self.path,
                self.httpversion[0],
                self.httpversion[1],
            )
        else:
            raise exceptions.HttpError(400, "Invalid request form")

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
                    e for e in encoding.ENCODINGS if e in self.headers.get_first("accept-encoding"))]

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
        parts = utils.parse_url(url)
        if not parts:
            raise ValueError("Invalid URL: %s" % url)
        self.scheme, self.host, self.port, self.path = parts

    @property
    def content(self):  # pragma: no cover
        # TODO: remove deprecated getter
        return self.body

    @content.setter
    def content(self, content):  # pragma: no cover
        # TODO: remove deprecated setter
        self.body = content


class EmptyRequest(Request):

    def __init__(
        self,
        form_in="",
        method="",
        scheme="",
        host="",
        port="",
        path="",
        httpversion=(0, 0),
        headers=None,
        body=""
    ):
        super(EmptyRequest, self).__init__(
            form_in=form_in,
            method=method,
            scheme=scheme,
            host=host,
            port=port,
            path=path,
            httpversion=httpversion,
            headers=(headers or odict.ODictCaseless()),
            body=body,
        )


class Response(object):
    _headers_to_strip_off = [
        'Proxy-Connection',
        'Alternate-Protocol',
        'Alt-Svc',
    ]

    def __init__(
        self,
        httpversion,
        status_code,
        msg=None,
        headers=None,
        body=None,
        sslinfo=None,
        timestamp_start=None,
        timestamp_end=None,
    ):
        if not headers:
            headers = odict.ODictCaseless()
        assert isinstance(headers, odict.ODictCaseless)

        self.httpversion = httpversion
        self.status_code = status_code
        self.msg = msg
        self.headers = headers
        self.body = body
        self.sslinfo = sslinfo
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

    def __eq__(self, other):
        try:
            self_d = [self.__dict__[k] for k in self.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            other_d = [other.__dict__[k] for k in other.__dict__ if k not in ('timestamp_start', 'timestamp_end')]
            return self_d == other_d
        except:
            return False

    def __repr__(self):
        # return "Response(%s - %s)" % (self.status_code, self.msg)

        if self.body:
            size = utils.pretty_size(len(self.body))
        else:
            size = "content missing"
        # TODO: Remove "(unknown content type, content missing)" edge-case
        return "<Response: {status_code} {msg} ({contenttype}, {size})>".format(
            status_code=self.status_code,
            msg=self.msg,
            contenttype=self.headers.get_first(
                "content-type",
                "unknown content type"),
            size=size)

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
            v = cookies.parse_set_cookie_header(header)
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
                cookies.format_set_cookie_header(
                    i[0],
                    i[1][0],
                    i[1][1]
                )
            )
        self.headers["Set-Cookie"] = values

    @property
    def content(self):  # pragma: no cover
        # TODO: remove deprecated getter
        return self.body

    @content.setter
    def content(self, content):  # pragma: no cover
        # TODO: remove deprecated setter
        self.body = content

    @property
    def code(self):  # pragma: no cover
        # TODO: remove deprecated getter
        return self.status_code

    @code.setter
    def code(self, code):  # pragma: no cover
        # TODO: remove deprecated setter
        self.status_code = code
