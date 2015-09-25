

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
