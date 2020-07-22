import time
from dataclasses import dataclass
from email.utils import formatdate, mktime_tz, parsedate_tz
from typing import Mapping
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Union

from mitmproxy.coretypes import multidict
from mitmproxy.net.http import cookies, message
from mitmproxy.net.http import status_codes
from mitmproxy.net.http.headers import Headers
from mitmproxy.utils import human
from mitmproxy.utils import strutils
from mitmproxy.utils.strutils import always_bytes


@dataclass
class ResponseData(message.MessageData):
    status_code: int
    reason: bytes


class Response(message.Message):
    """
    An HTTP response.
    """
    data: ResponseData

    def __init__(
            self,
            http_version: bytes,
            status_code: int,
            reason: bytes,
            headers: Union[Headers, Tuple[Tuple[bytes, bytes], ...]],
            content: Optional[bytes],
            trailers: Union[None, Headers, Tuple[Tuple[bytes, bytes], ...]],
            timestamp_start: float,
            timestamp_end: Optional[float],
    ):
        # auto-convert invalid types to retain compatibility with older code.
        if isinstance(http_version, str):
            http_version = http_version.encode("ascii", "strict")
        if isinstance(reason, str):
            reason = reason.encode("ascii", "strict")

        if isinstance(content, str):
            raise ValueError("Content must be bytes, not {}".format(type(content).__name__))
        if not isinstance(headers, Headers):
            headers = Headers(headers)
        if trailers is not None and not isinstance(trailers, Headers):
            trailers = Headers(trailers)

        self.data = ResponseData(
            http_version=http_version,
            status_code=status_code,
            reason=reason,
            headers=headers,
            content=content,
            trailers=trailers,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

    def __repr__(self) -> str:
        if self.raw_content:
            ct = self.headers.get("content-type", "unknown content type")
            size = human.pretty_size(len(self.raw_content))
            details = f"{ct}, {size}"
        else:
            details = "no content"
        return f"Response({self.status_code}, {details})"

    @classmethod
    def make(
            cls,
            status_code: int = 200,
            content: Union[bytes, str] = b"",
            headers: Union[Headers, Mapping[str, Union[str, bytes]], Iterable[Tuple[bytes, bytes]]] = ()
    ) -> "Response":
        """
        Simplified API for creating response objects.
        """
        if isinstance(headers, Headers):
            headers = headers
        elif isinstance(headers, dict):
            headers = Headers(
                (always_bytes(k, "utf-8", "surrogateescape"),
                 always_bytes(v, "utf-8", "surrogateescape"))
                for k, v in headers.items()
            )
        elif isinstance(headers, Iterable):
            headers = Headers(headers)
        else:
            raise TypeError("Expected headers to be an iterable or dict, but is {}.".format(
                type(headers).__name__
            ))

        resp = cls(
            b"HTTP/1.1",
            status_code,
            status_codes.RESPONSES.get(status_code, "").encode(),
            headers,
            None,
            None,
            time.time(),
            time.time(),
        )

        # Assign this manually to update the content-length header.
        if isinstance(content, bytes):
            resp.content = content
        elif isinstance(content, str):
            resp.text = content
        else:
            raise TypeError(f"Expected content to be str or bytes, but is {type(content).__name__}.")

        return resp

    @property
    def status_code(self) -> int:
        """
        HTTP Status Code, e.g. ``200``.
        """
        return self.data.status_code

    @status_code.setter
    def status_code(self, status_code: int) -> None:
        self.data.status_code = status_code

    @property
    def reason(self) -> str:
        """
        HTTP Reason Phrase, e.g. "Not Found".
        HTTP/2 responses do not contain a reason phrase, an empty string will be returned instead.
        """
        # Encoding: http://stackoverflow.com/a/16674906/934719
        return self.data.reason.decode("ISO-8859-1")

    @reason.setter
    def reason(self, reason: Union[str, bytes]) -> None:
        self.data.reason = strutils.always_bytes(reason, "ISO-8859-1")

    def _get_cookies(self):
        h = self.headers.get_all("set-cookie")
        all_cookies = cookies.parse_set_cookie_headers(h)
        return tuple(
            (name, (value, attrs))
            for name, value, attrs in all_cookies
        )

    def _set_cookies(self, value):
        cookie_headers = []
        for k, v in value:
            header = cookies.format_set_cookie_header([(k, v[0], v[1])])
            cookie_headers.append(header)
        self.headers.set_all("set-cookie", cookie_headers)

    @property
    def cookies(self) -> multidict.MultiDictView:
        """
        The response cookies. A possibly empty
        :py:class:`~mitmproxy.net.multidict.MultiDictView`, where the keys are cookie
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
                    self.headers[i] = formatdate(new, usegmt=True)
        c = []
        for set_cookie_header in self.headers.get_all("set-cookie"):
            try:
                refreshed = cookies.refresh_set_cookie_header(set_cookie_header, delta)
            except ValueError:
                refreshed = set_cookie_header
            c.append(refreshed)
        if c:
            self.headers.set_all("set-cookie", c)
