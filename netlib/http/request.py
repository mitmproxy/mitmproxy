from __future__ import absolute_import, print_function, division

import re

import six
from six.moves import urllib

from netlib import multidict
from netlib import strutils
from netlib.http import multipart
from netlib.http import cookies
from netlib.http import headers as nheaders
from netlib.http import message
import netlib.http.url

# This regex extracts & splits the host header into host and port.
# Handles the edge case of IPv6 addresses containing colons.
# https://bugzilla.mozilla.org/show_bug.cgi?id=45891
host_header_re = re.compile(r"^(?P<host>[^:]+|\[.+\])(?::(?P<port>\d+))?$")


class RequestData(message.MessageData):
    def __init__(
        self,
        first_line_format,
        method,
        scheme,
        host,
        port,
        path,
        http_version,
        headers=(),
        content=None,
        timestamp_start=None,
        timestamp_end=None
    ):
        if isinstance(method, six.text_type):
            method = method.encode("ascii", "strict")
        if isinstance(scheme, six.text_type):
            scheme = scheme.encode("ascii", "strict")
        if isinstance(host, six.text_type):
            host = host.encode("idna", "strict")
        if isinstance(path, six.text_type):
            path = path.encode("ascii", "strict")
        if isinstance(http_version, six.text_type):
            http_version = http_version.encode("ascii", "strict")
        if not isinstance(headers, nheaders.Headers):
            headers = nheaders.Headers(headers)
        if isinstance(content, six.text_type):
            raise ValueError("Content must be bytes, not {}".format(type(content).__name__))

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


class Request(message.Message):
    """
    An HTTP request.
    """
    def __init__(self, *args, **kwargs):
        super(Request, self).__init__()
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
        if isinstance(pattern, six.text_type):
            pattern = strutils.escaped_str_to_bytes(pattern)
        if isinstance(repl, six.text_type):
            repl = strutils.escaped_str_to_bytes(repl)

        c = super(Request, self).replace(pattern, repl, flags)
        self.path, pc = re.subn(
            pattern, repl, self.data.path, flags=flags
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
        return message._native(self.data.method).upper()

    @method.setter
    def method(self, method):
        self.data.method = message._always_bytes(method)

    @property
    def scheme(self):
        """
        HTTP request scheme, which should be "http" or "https".
        """
        if not self.data.scheme:
            return self.data.scheme
        return message._native(self.data.scheme)

    @scheme.setter
    def scheme(self, scheme):
        self.data.scheme = message._always_bytes(scheme)

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
        Guaranteed to start with a slash, except for OPTIONS requests, which may just be "*".
        """
        if self.data.path is None:
            return None
        else:
            return message._native(self.data.path)

    @path.setter
    def path(self, path):
        self.data.path = message._always_bytes(path)

    @property
    def url(self):
        """
        The URL string, constructed from the request's URL components
        """
        if self.first_line_format == "authority":
            return "%s:%d" % (self.host, self.port)
        return netlib.http.url.unparse(self.scheme, self.host, self.port, self.path)

    @url.setter
    def url(self, url):
        self.scheme, self.host, self.port, self.path = netlib.http.url.parse(url)

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
        return netlib.http.url.unparse(self.scheme, self.pretty_host, self.port, self.path)

    @property
    def query(self):
        # type: () -> multidict.MultiDictView
        """
        The request query string as an :py:class:`~netlib.multidict.MultiDictView` object.
        """
        return multidict.MultiDictView(
            self._get_query,
            self._set_query
        )

    def _get_query(self):
        query = urllib.parse.urlparse(self.url).query
        return tuple(netlib.http.url.decode(query))

    def _set_query(self, query_data):
        query = netlib.http.url.encode(query_data)
        _, _, path, params, _, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

    @query.setter
    def query(self, value):
        self._set_query(value)

    @property
    def cookies(self):
        # type: () -> multidict.MultiDictView
        """
        The request cookies.

        An empty :py:class:`~netlib.multidict.MultiDictView` object if the cookie monster ate them all.
        """
        return multidict.MultiDictView(
            self._get_cookies,
            self._set_cookies
        )

    def _get_cookies(self):
        h = self.headers.get_all("Cookie")
        return tuple(cookies.parse_cookie_headers(h))

    def _set_cookies(self, value):
        self.headers["cookie"] = cookies.format_cookie_header(value)

    @cookies.setter
    def cookies(self, value):
        self._set_cookies(value)

    @property
    def path_components(self):
        """
        The URL's path components as a tuple of strings.
        Components are unquoted.
        """
        path = urllib.parse.urlparse(self.url).path
        # This needs to be a tuple so that it's immutable.
        # Otherwise, this would fail silently:
        #   request.path_components.append("foo")
        return tuple(netlib.http.url.unquote(i) for i in path.split("/") if i)

    @path_components.setter
    def path_components(self, components):
        components = map(lambda x: netlib.http.url.quote(x, safe=""), components)
        path = "/" + "/".join(components)
        _, _, _, params, query, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

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
                    for e in {"gzip", "identity", "deflate", "br"}
                    if e in accept_encoding
                )
            )

    @property
    def urlencoded_form(self):
        """
        The URL-encoded form data as an :py:class:`~netlib.multidict.MultiDictView` object.
        An empty multidict.MultiDictView if the content-type indicates non-form data
        or the content could not be parsed.
        """
        return multidict.MultiDictView(
            self._get_urlencoded_form,
            self._set_urlencoded_form
        )

    def _get_urlencoded_form(self):
        is_valid_content_type = "application/x-www-form-urlencoded" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            try:
                return tuple(netlib.http.url.decode(self.content))
            except ValueError:
                pass
        return ()

    def _set_urlencoded_form(self, form_data):
        """
        Sets the body to the URL-encoded form data, and adds the appropriate content-type header.
        This will overwrite the existing content if there is one.
        """
        self.headers["content-type"] = "application/x-www-form-urlencoded"
        self.content = netlib.http.url.encode(form_data).encode()

    @urlencoded_form.setter
    def urlencoded_form(self, value):
        self._set_urlencoded_form(value)

    @property
    def multipart_form(self):
        """
        The multipart form data as an :py:class:`~netlib.multidict.MultiDictView` object.
        None if the content-type indicates non-form data.
        """
        return multidict.MultiDictView(
            self._get_multipart_form,
            self._set_multipart_form
        )

    def _get_multipart_form(self):
        is_valid_content_type = "multipart/form-data" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            try:
                return multipart.decode(self.headers, self.content)
            except ValueError:
                pass
        return ()

    def _set_multipart_form(self, value):
        raise NotImplementedError()

    @multipart_form.setter
    def multipart_form(self, value):
        self._set_multipart_form(value)
