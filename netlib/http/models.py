from __future__ import absolute_import, print_function, division
import copy

from ..odict import ODict
from .. import utils, encoding
from ..utils import always_bytes, always_byte_args
from . import cookies

import six
from six.moves import urllib
try:
    from collections import MutableMapping
except ImportError:
    from collections.abc import MutableMapping

# TODO: Move somewhere else?
ALPN_PROTO_HTTP1 = b'http/1.1'
ALPN_PROTO_H2 = b'h2'
HDR_FORM_URLENCODED = b"application/x-www-form-urlencoded"
HDR_FORM_MULTIPART = b"multipart/form-data"

CONTENT_MISSING = 0


class Headers(MutableMapping, object):
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

    @always_byte_args("ascii")
    def __init__(self, fields=None, **headers):
        """
        Args:
            fields: (optional) list of ``(name, value)`` header tuples,
                e.g. ``[("Host","example.com")]``. All names and values must be bytes.
            **headers: Additional headers to set. Will overwrite existing values from `fields`.
                For convenience, underscores in header names will be transformed to dashes -
                this behaviour does not extend to other methods.
                If ``**headers`` contains multiple keys that have equal ``.lower()`` s,
                the behavior is undefined.
        """
        self.fields = fields or []

        # content_type -> content-type
        headers = {
            name.encode("ascii").replace(b"_", b"-"): value
            for name, value in six.iteritems(headers)
        }
        self.update(headers)

    def __bytes__(self):
        return b"\r\n".join(b": ".join(field) for field in self.fields) + b"\r\n"

    if six.PY2:
        __str__ = __bytes__

    @always_byte_args("ascii")
    def __getitem__(self, name):
        values = self.get_all(name)
        if not values:
            raise KeyError(name)
        return b", ".join(values)

    @always_byte_args("ascii")
    def __setitem__(self, name, value):
        idx = self._index(name)

        # To please the human eye, we insert at the same position the first existing header occured.
        if idx is not None:
            del self[name]
            self.fields.insert(idx, [name, value])
        else:
            self.fields.append([name, value])

    @always_byte_args("ascii")
    def __delitem__(self, name):
        if name not in self:
            raise KeyError(name)
        name = name.lower()
        self.fields = [
            field for field in self.fields
            if name != field[0].lower()
        ]

    def __iter__(self):
        seen = set()
        for name, _ in self.fields:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                yield name

    def __len__(self):
        return len(set(name.lower() for name, _ in self.fields))

    # __hash__ = object.__hash__

    def _index(self, name):
        name = name.lower()
        for i, field in enumerate(self.fields):
            if field[0].lower() == name:
                return i
        return None

    def __eq__(self, other):
        if isinstance(other, Headers):
            return self.fields == other.fields
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @always_byte_args("ascii")
    def get_all(self, name):
        """
        Like :py:meth:`get`, but does not fold multiple headers into a single one.
        This is useful for Set-Cookie headers, which do not support folding.

        See also: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        name_lower = name.lower()
        values = [value for n, value in self.fields if n.lower() == name_lower]
        return values

    def set_all(self, name, values):
        """
        Explicitly set multiple headers for the given key.
        See: :py:meth:`get_all`
        """
        name = always_bytes(name, "ascii")
        values = (always_bytes(value, "ascii") for value in values)
        if name in self:
            del self[name]
        self.fields.extend(
            [name, value] for value in values
        )

    def copy(self):
        return Headers(copy.copy(self.fields))

    # Implement the StateObject protocol from mitmproxy
    def get_state(self, short=False):
        return tuple(tuple(field) for field in self.fields)

    def load_state(self, state):
        self.fields = [list(field) for field in state]

    @classmethod
    def from_state(cls, state):
        return cls([list(field) for field in state])


class Message(object):
    def __init__(self, http_version, headers, body, timestamp_start, timestamp_end):
        self.http_version = http_version
        if not headers:
            headers = Headers()
        assert isinstance(headers, Headers)
        self.headers = headers

        self._body = body
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body):
        self._body = body
        if isinstance(body, bytes):
            self.headers[b"Content-Length"] = str(len(body)).encode()

    content = body

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.__dict__ == other.__dict__
        return False


class Request(Message):
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
            http_version,
            headers=None,
            body=None,
            timestamp_start=None,
            timestamp_end=None,
            form_out=None
    ):
        super(Request, self).__init__(http_version, headers, body, timestamp_start, timestamp_end)

        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.form_out = form_out or form_in

    def __repr__(self):
        if self.host and self.port:
            hostport = "{}:{}".format(self.host, self.port)
        else:
            hostport = ""
        path = self.path or ""
        return "HTTPRequest({} {}{})".format(
            self.method, hostport, path
        )

    def anticache(self):
        """
            Modifies this request to remove headers that might produce a cached
            response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            b"If-Modified-Since",
            b"If-None-Match",
        ]
        for i in delheaders:
            self.headers.pop(i, None)

    def anticomp(self):
        """
            Modifies this request to remove headers that will compress the
            resource's data.
        """
        self.headers["Accept-Encoding"] = b"identity"

    def constrain_encoding(self):
        """
            Limits the permissible Accept-Encoding values, based on what we can
            decode appropriately.
        """
        accept_encoding = self.headers.get(b"Accept-Encoding")
        if accept_encoding:
            self.headers["Accept-Encoding"] = (
                ', '.join(
                    e
                    for e in encoding.ENCODINGS
                    if e in accept_encoding
                )
            )

    def update_host_header(self):
        """
            Update the host header to reflect the current target.
        """
        self.headers["Host"] = self.host

    def get_form(self):
        """
            Retrieves the URL-encoded or multipart form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body:
            if HDR_FORM_URLENCODED in self.headers.get("Content-Type", "").lower():
                return self.get_form_urlencoded()
            elif HDR_FORM_MULTIPART in self.headers.get("Content-Type", "").lower():
                return self.get_form_multipart()
        return ODict([])

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body and HDR_FORM_URLENCODED in self.headers.get("Content-Type", "").lower():
            return ODict(utils.urldecode(self.body))
        return ODict([])

    def get_form_multipart(self):
        if self.body and HDR_FORM_MULTIPART in self.headers.get("Content-Type", "").lower():
            return ODict(
                utils.multipartdecode(
                    self.headers,
                    self.body))
        return ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        # FIXME: If there's an existing content-type header indicating a
        # url-encoded form, leave it alone.
        self.headers[b"Content-Type"] = HDR_FORM_URLENCODED
        self.body = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urllib.parse.urlparse(self.url)
        return [urllib.parse.unquote(i) for i in path.split(b"/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.parse.quote(i, safe="") for i in lst]
        path = b"/" + b"/".join(lst)
        scheme, netloc, _, params, query, fragment = urllib.parse.urlparse(self.url)
        self.url = urllib.parse.urlunparse(
            [scheme, netloc, path, params, query, fragment]
        )

    def get_query(self):
        """
            Gets the request query string. Returns an ODict object.
        """
        _, _, _, _, query, _ = urllib.parse.urlparse(self.url)
        if query:
            return ODict(utils.urldecode(query))
        return ODict([])

    def set_query(self, odict):
        """
            Takes an ODict object, and sets the request query string.
        """
        scheme, netloc, path, params, _, fragment = urllib.parse.urlparse(self.url)
        query = utils.urlencode(odict.lst)
        self.url = urllib.parse.urlunparse(
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
        if hostheader and "Host" in self.headers:
            try:
                return self.headers["Host"].decode("idna")
            except ValueError:
                pass
        if self.host:
            return self.host.decode("idna")

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
        ret = ODict()
        for i in self.headers.get_all("Cookie"):
            ret.extend(cookies.parse_cookie_header(i))
        return ret

    def set_cookies(self, odict):
        """
            Takes an netlib.odict.ODict object. Over-writes any existing Cookie
            headers.
        """
        v = cookies.format_cookie_header(odict)
        self.headers["Cookie"] = v

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

            Raises:
                ValueError if the URL was invalid
        """
        # TODO: Should handle incoming unicode here.
        parts = utils.parse_url(url)
        if not parts:
            raise ValueError("Invalid URL: %s" % url)
        self.scheme, self.host, self.port, self.path = parts


class Response(Message):
    _headers_to_strip_off = [
        'Proxy-Connection',
        'Alternate-Protocol',
        'Alt-Svc',
    ]

    def __init__(
            self,
            http_version,
            status_code,
            msg=None,
            headers=None,
            body=None,
            timestamp_start=None,
            timestamp_end=None,
    ):
        super(Response, self).__init__(http_version, headers, body, timestamp_start, timestamp_end)
        self.status_code = status_code
        self.msg = msg

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
            contenttype=self.headers.get("Content-Type", "unknown content type"),
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
        for header in self.headers.get_all("Set-Cookie"):
            v = cookies.parse_set_cookie_header(header)
            if v:
                name, value, attrs = v
                ret.append([name, [value, attrs]])
        return ODict(ret)

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
        self.headers.set_all("Set-Cookie", values)
