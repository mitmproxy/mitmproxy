from __future__ import absolute_import, print_function, division

import re
import warnings

import six
from six.moves import urllib

from netlib import utils
from netlib.http import cookies
from netlib.odict import ODict
from .. import encoding
from .headers import Headers
from .message import Message, _native, _always_bytes, MessageData

# This regex extracts & splits the host header into host and port.
# Handles the edge case of IPv6 addresses containing colons.
# https://bugzilla.mozilla.org/show_bug.cgi?id=45891
host_header_re = re.compile(r"^(?P<host>[^:]+|\[.+\])(?::(?P<port>\d+))?$")

class RequestData(MessageData):
    def __init__(self, first_line_format, method, scheme, host, port, path, http_version, headers=None, content=None,
                 timestamp_start=None, timestamp_end=None):
        if not isinstance(headers, Headers):
            headers = Headers(headers)

        self.first_line_format = first_line_format
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.http_version = http_version
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


class Request(Message):
    """
    An HTTP request.
    """
    def __init__(self, *args, **kwargs):
        self.data = RequestData(*args, **kwargs)

    def __repr__(self):
        if self.host and self.port:
            hostport = "{}:{}".format(self.host, self.port)
        else:
            hostport = ""
        path = self.path or ""
        return "Request({} {}{})".format(
            self.method, hostport, path
        )

    def replace(self, pattern, repl, flags=0):
        """
            Replaces a regular expression pattern with repl in the headers, the
            request path and the body of the request. Encoded content will be
            decoded before replacement, and re-encoded afterwards.

            Returns:
                The number of replacements made.
        """
        # TODO: Proper distinction between text and bytes.
        c = super(Request, self).replace(pattern, repl, flags)
        self.path, pc = utils.safe_subn(
            pattern, repl, self.path, flags=flags
        )
        c += pc
        return c

    @property
    def first_line_format(self):
        """
        HTTP request form as defined in `RFC7230 <https://tools.ietf.org/html/rfc7230#section-5.3>`_.

        origin-form and asterisk-form are subsumed as "relative".
        """
        return self.data.first_line_format

    @first_line_format.setter
    def first_line_format(self, first_line_format):
        self.data.first_line_format = first_line_format

    @property
    def method(self):
        """
        HTTP request method, e.g. "GET".
        """
        return _native(self.data.method).upper()

    @method.setter
    def method(self, method):
        self.data.method = _always_bytes(method)

    @property
    def scheme(self):
        """
        HTTP request scheme, which should be "http" or "https".
        """
        return _native(self.data.scheme)

    @scheme.setter
    def scheme(self, scheme):
        self.data.scheme = _always_bytes(scheme)

    @property
    def host(self):
        """
        Target host. This may be parsed from the raw request
        (e.g. from a ``GET http://example.com/ HTTP/1.1`` request line)
        or inferred from the proxy mode (e.g. an IP in transparent mode).

        Setting the host attribute also updates the host header, if present.
        """

        if six.PY2:  # pragma: no cover
            return self.data.host

        if not self.data.host:
            return self.data.host
        try:
            return self.data.host.decode("idna")
        except UnicodeError:
            return self.data.host.decode("utf8", "surrogateescape")

    @host.setter
    def host(self, host):
        if isinstance(host, six.text_type):
            try:
                # There's no non-strict mode for IDNA encoding.
                # We don't want this operation to fail though, so we try
                # utf8 as a last resort.
                host = host.encode("idna", "strict")
            except UnicodeError:
                host = host.encode("utf8", "surrogateescape")

        self.data.host = host

        # Update host header
        if "host" in self.headers:
            if host:
                self.headers["host"] = host
            else:
                self.headers.pop("host")

    @property
    def port(self):
        """
        Target port
        """
        return self.data.port

    @port.setter
    def port(self, port):
        self.data.port = port

    @property
    def path(self):
        """
        HTTP request path, e.g. "/index.html".
        Guaranteed to start with a slash.
        """
        if self.data.path is None:
            return None
        else:
            return _native(self.data.path)

    @path.setter
    def path(self, path):
        self.data.path = _always_bytes(path)

    @property
    def url(self):
        """
        The URL string, constructed from the request's URL components
        """
        return utils.unparse_url(self.scheme, self.host, self.port, self.path)

    @url.setter
    def url(self, url):
        self.scheme, self.host, self.port, self.path = utils.parse_url(url)

    def _parse_host_header(self):
        """Extract the host and port from Host header"""
        if "host" not in self.headers:
            return None, None
        host, port = self.headers["host"], None
        m = host_header_re.match(host)
        if m:
            host = m.group("host").strip("[]")
            if m.group("port"):
                port = int(m.group("port"))
        return host, port

    @property
    def pretty_host(self):
        """
        Similar to :py:attr:`host`, but using the Host headers as an additional preferred data source.
        This is useful in transparent mode where :py:attr:`host` is only an IP address,
        but may not reflect the actual destination as the Host header could be spoofed.
        """
        host, port = self._parse_host_header()
        if not host:
            return self.host
        if not port:
            port = 443 if self.scheme == 'https' else 80
        # Prefer the original address if host header has an unexpected form
        return host if port == self.port else self.host

    @property
    def pretty_url(self):
        """
        Like :py:attr:`url`, but using :py:attr:`pretty_host` instead of :py:attr:`host`.
        """
        if self.first_line_format == "authority":
            return "%s:%d" % (self.pretty_host, self.port)
        return utils.unparse_url(self.scheme, self.pretty_host, self.port, self.path)

    @property
    def query(self):
        """
        The request query string as an :py:class:`ODict` object.
        None, if there is no query.
        """
        _, _, _, _, query, _ = urllib.parse.urlparse(self.url)
        if query:
            return ODict(utils.urldecode(query))
        return None

    @query.setter
    def query(self, odict):
        query = utils.urlencode(odict.lst)
        scheme, netloc, path, params, _, fragment = urllib.parse.urlparse(self.url)
        _, _, _, self.path = utils.parse_url(
                urllib.parse.urlunparse([scheme, netloc, path, params, query, fragment]))

    @property
    def cookies(self):
        """
        The request cookies.
        An empty :py:class:`ODict` object if the cookie monster ate them all.
        """
        ret = ODict()
        for i in self.headers.get_all("Cookie"):
            ret.extend(cookies.parse_cookie_header(i))
        return ret

    @cookies.setter
    def cookies(self, odict):
        self.headers["cookie"] = cookies.format_cookie_header(odict)

    @property
    def path_components(self):
        """
        The URL's path components as a list of strings.
        Components are unquoted.
        """
        _, _, path, _, _, _ = urllib.parse.urlparse(self.url)
        return [urllib.parse.unquote(i) for i in path.split("/") if i]

    @path_components.setter
    def path_components(self, components):
        components = map(lambda x: urllib.parse.quote(x, safe=""), components)
        path = "/" + "/".join(components)
        scheme, netloc, _, params, query, fragment = urllib.parse.urlparse(self.url)
        _, _, _, self.path = utils.parse_url(
                urllib.parse.urlunparse([scheme, netloc, path, params, query, fragment]))

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
            self.headers.pop(i, None)

    def anticomp(self):
        """
        Modifies this request to remove headers that will compress the
        resource's data.
        """
        self.headers["accept-encoding"] = "identity"

    def constrain_encoding(self):
        """
        Limits the permissible Accept-Encoding values, based on what we can
        decode appropriately.
        """
        accept_encoding = self.headers.get("accept-encoding")
        if accept_encoding:
            self.headers["accept-encoding"] = (
                ', '.join(
                    e
                    for e in encoding.ENCODINGS
                    if e in accept_encoding
                )
            )

    @property
    def urlencoded_form(self):
        """
        The URL-encoded form data as an :py:class:`ODict` object.
        None if there is no data or the content-type indicates non-form data.
        """
        is_valid_content_type = "application/x-www-form-urlencoded" in self.headers.get("content-type", "").lower()
        if self.content and is_valid_content_type:
            return ODict(utils.urldecode(self.content))
        return None

    @urlencoded_form.setter
    def urlencoded_form(self, odict):
        """
        Sets the body to the URL-encoded form data, and adds the appropriate content-type header.
        This will overwrite the existing content if there is one.
        """
        self.headers["content-type"] = "application/x-www-form-urlencoded"
        self.content = utils.urlencode(odict.lst)

    @property
    def multipart_form(self):
        """
        The multipart form data as an :py:class:`ODict` object.
        None if there is no data or the content-type indicates non-form data.
        """
        is_valid_content_type = "multipart/form-data" in self.headers.get("content-type", "").lower()
        if self.content and is_valid_content_type:
            return ODict(utils.multipartdecode(self.headers,self.content))
        return None

    @multipart_form.setter
    def multipart_form(self, value):
        raise NotImplementedError()

    # Legacy

    def get_cookies(self):  # pragma: no cover
        warnings.warn(".get_cookies is deprecated, use .cookies instead.", DeprecationWarning)
        return self.cookies

    def set_cookies(self, odict):  # pragma: no cover
        warnings.warn(".set_cookies is deprecated, use .cookies instead.", DeprecationWarning)
        self.cookies = odict

    def get_query(self):  # pragma: no cover
        warnings.warn(".get_query is deprecated, use .query instead.", DeprecationWarning)
        return self.query or ODict([])

    def set_query(self, odict):  # pragma: no cover
        warnings.warn(".set_query is deprecated, use .query instead.", DeprecationWarning)
        self.query = odict

    def get_path_components(self):  # pragma: no cover
        warnings.warn(".get_path_components is deprecated, use .path_components instead.", DeprecationWarning)
        return self.path_components

    def set_path_components(self, lst):  # pragma: no cover
        warnings.warn(".set_path_components is deprecated, use .path_components instead.", DeprecationWarning)
        self.path_components = lst

    def get_form_urlencoded(self):  # pragma: no cover
        warnings.warn(".get_form_urlencoded is deprecated, use .urlencoded_form instead.", DeprecationWarning)
        return self.urlencoded_form or ODict([])

    def set_form_urlencoded(self, odict):  # pragma: no cover
        warnings.warn(".set_form_urlencoded is deprecated, use .urlencoded_form instead.", DeprecationWarning)
        self.urlencoded_form = odict

    def get_form_multipart(self):  # pragma: no cover
        warnings.warn(".get_form_multipart is deprecated, use .multipart_form instead.", DeprecationWarning)
        return self.multipart_form or ODict([])
