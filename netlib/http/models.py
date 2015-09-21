

from ..odict import ODict
from .. import utils, encoding
from ..utils import always_bytes, native
from . import cookies
from .headers import Headers

from six.moves import urllib

# TODO: Move somewhere else?
ALPN_PROTO_HTTP1 = b'http/1.1'
ALPN_PROTO_H2 = b'h2'
HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
HDR_FORM_MULTIPART = "multipart/form-data"

CONTENT_MISSING = 0


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
            self.headers["content-length"] = str(len(body)).encode()

    content = body

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.__dict__ == other.__dict__
        return False


class Request(Message):
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
            hostport = "{}:{}".format(native(self.host,"idna"), self.port)
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

    def update_host_header(self):
        """
            Update the host header to reflect the current target.
        """
        self.headers["host"] = self.host

    def get_form(self):
        """
            Retrieves the URL-encoded or multipart form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body:
            if HDR_FORM_URLENCODED in self.headers.get("content-type", "").lower():
                return self.get_form_urlencoded()
            elif HDR_FORM_MULTIPART in self.headers.get("content-type", "").lower():
                return self.get_form_multipart()
        return ODict([])

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.body and HDR_FORM_URLENCODED in self.headers.get("content-type", "").lower():
            return ODict(utils.urldecode(self.body))
        return ODict([])

    def get_form_multipart(self):
        if self.body and HDR_FORM_MULTIPART in self.headers.get("content-type", "").lower():
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
        self.headers["content-type"] = HDR_FORM_URLENCODED
        self.body = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urllib.parse.urlparse(self.url)
        return [urllib.parse.unquote(native(i,"ascii")) for i in path.split(b"/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.parse.quote(i, safe="") for i in lst]
        path = always_bytes("/" + "/".join(lst))
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
        if hostheader and "host" in self.headers:
            try:
                return self.headers["host"]
            except ValueError:
                pass
        if self.host:
            return self.host.decode("idna")

    def pretty_url(self, hostheader):
        if self.form_out == "authority":  # upstream proxy mode
            return b"%s:%d" % (always_bytes(self.pretty_host(hostheader)), self.port)
        return utils.unparse_url(self.scheme,
                                 self.pretty_host(hostheader),
                                 self.port,
                                 self.path)

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
        self.headers["cookie"] = v

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
        )

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
            contenttype=self.headers.get("content-type", "unknown content type"),
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
        for header in self.headers.get_all("set-cookie"):
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
        self.headers.set_all("set-cookie", values)
