from __future__ import absolute_import, print_function, division

from email.utils import parsedate_tz, formatdate, mktime_tz
import time

from . import cookies
from .headers import Headers
from .message import Message, _native, _always_bytes, MessageData
from ..multidict import MultiDictView
from .. import utils


class ResponseData(MessageData):
    def __init__(self, http_version, status_code, reason=None, headers=(), content=None,
                 timestamp_start=None, timestamp_end=None):
        if not isinstance(headers, Headers):
            headers = Headers(headers)

        self.http_version = http_version
        self.status_code = status_code
        self.reason = reason
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


class Response(Message):
    """
    An HTTP response.
    """
    def __init__(self, *args, **kwargs):
        self.data = ResponseData(*args, **kwargs)

    def __repr__(self):
        if self.content:
            details = "{}, {}".format(
                self.headers.get("content-type", "unknown content type"),
                utils.pretty_size(len(self.content))
            )
        else:
            details = "no content"
        return "Response({status_code} {reason}, {details})".format(
            status_code=self.status_code,
            reason=self.reason,
            details=details
        )

    @property
    def status_code(self):
        """
        HTTP Status Code, e.g. ``200``.
        """
        return self.data.status_code

    @status_code.setter
    def status_code(self, status_code):
        self.data.status_code = status_code

    @property
    def reason(self):
        """
        HTTP Reason Phrase, e.g. "Not Found".
        This is always :py:obj:`None` for HTTP2 requests, because HTTP2 responses do not contain a reason phrase.
        """
        return _native(self.data.reason)

    @reason.setter
    def reason(self, reason):
        self.data.reason = _always_bytes(reason)

    @property
    def cookies(self):
        # type: () -> MultiDictView
        """
        The response cookies. A possibly empty :py:class:`MultiDictView`, where the keys are
        cookie name strings, and values are (value, attr) tuples. Value is a string, and attr is
        an ODictCaseless containing cookie attributes. Within attrs, unary attributes (e.g. HTTPOnly)
        are indicated by a Null value.

        Caveats:
            Updating the attr
        """
        return MultiDictView(
            self._get_cookies,
            self._set_cookies
        )

    def _get_cookies(self):
        h = self.headers.get_all("set-cookie")
        return tuple(cookies.parse_set_cookie_headers(h))

    def _set_cookies(self, value):
        cookie_headers = []
        for k, v in value:
            header = cookies.format_set_cookie_header(k, v[0], v[1])
            cookie_headers.append(header)
        self.headers.set_all("set-cookie", cookie_headers)

    @cookies.setter
    def cookies(self, value):
        self._set_cookies(value)

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
                refreshed = cookies.refresh_set_cookie_header(set_cookie_header, delta)
            except ValueError:
                refreshed = set_cookie_header
            c.append(refreshed)
        if c:
            self.headers.set_all("set-cookie", c)
