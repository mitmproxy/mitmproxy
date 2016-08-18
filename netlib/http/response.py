from __future__ import absolute_import, print_function, division

import six
import time
from email.utils import parsedate_tz, formatdate, mktime_tz
from netlib import human
from netlib import multidict
from netlib.http import cookies
from netlib.http import headers as nheaders
from netlib.http import message
from netlib.http import status_codes
from typing import AnyStr  # noqa
from typing import Dict  # noqa
from typing import Iterable  # noqa
from typing import Tuple  # noqa
from typing import Union  # noqa


class ResponseData(message.MessageData):
    def __init__(
        self,
        http_version,
        status_code,
        reason=None,
        headers=(),
        content=None,
        timestamp_start=None,
        timestamp_end=None
    ):
        if isinstance(http_version, six.text_type):
            http_version = http_version.encode("ascii", "strict")
        if isinstance(reason, six.text_type):
            reason = reason.encode("ascii", "strict")
        if not isinstance(headers, nheaders.Headers):
            headers = nheaders.Headers(headers)
        if isinstance(content, six.text_type):
            raise ValueError("Content must be bytes, not {}".format(type(content).__name__))

        self.http_version = http_version
        self.status_code = status_code
        self.reason = reason
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


class Response(message.Message):
    """
    An HTTP response.
    """
    def __init__(self, *args, **kwargs):
        super(Response, self).__init__()
        self.data = ResponseData(*args, **kwargs)

    def __repr__(self):
        if self.raw_content:
            details = "{}, {}".format(
                self.headers.get("content-type", "unknown content type"),
                human.pretty_size(len(self.raw_content))
            )
        else:
            details = "no content"
        return "Response({status_code} {reason}, {details})".format(
            status_code=self.status_code,
            reason=self.reason,
            details=details
        )

    @classmethod
    def make(
            cls,
            status_code=200,  # type: int
            content=b"",  # type: AnyStr
            headers=()  # type: Union[Dict[AnyStr, AnyStr], Iterable[Tuple[bytes, bytes]]]
    ):
        """
        Simplified API for creating response objects.
        """
        resp = cls(
            b"HTTP/1.1",
            status_code,
            status_codes.RESPONSES.get(status_code, "").encode(),
            (),
            None
        )
        # Assign this manually to update the content-length header.
        if isinstance(content, bytes):
            resp.content = content
        elif isinstance(content, str):
            resp.text = content
        else:
            raise TypeError("Expected content to be str or bytes, but is {}.".format(
                type(content).__name__
            ))

        # Headers can be list or dict, we differentiate here.
        if isinstance(headers, dict):
            resp.headers = nheaders.Headers(**headers)
        elif isinstance(headers, Iterable):
            resp.headers = nheaders.Headers(headers)
        else:
            raise TypeError("Expected headers to be an iterable or dict, but is {}.".format(
                type(headers).__name__
            ))

        return resp

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
        return message._native(self.data.reason)

    @reason.setter
    def reason(self, reason):
        self.data.reason = message._always_bytes(reason)

    @property
    def cookies(self):
        # type: () -> multidict.MultiDictView
        """
        The response cookies. A possibly empty
        :py:class:`~netlib.multidict.MultiDictView`, where the keys are cookie
        name strings, and values are (value, attr) tuples. Value is a string,
        and attr is an MultiDictView containing cookie attributes. Within
        attrs, unary attributes (e.g. HTTPOnly) are indicated by a Null value.

        Caveats:
            Updating the attr
        """
        return multidict.MultiDictView(
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
