import binascii
import os
import re
import time
import urllib.parse
import json
from dataclasses import dataclass
from dataclasses import fields
from email.utils import formatdate
from email.utils import mktime_tz
from email.utils import parsedate_tz
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Union
from typing import cast
from typing import Any

from mitmproxy import flow
from mitmproxy.websocket import WebSocketData
from mitmproxy.coretypes import multidict
from mitmproxy.coretypes import serializable
from mitmproxy.net import encoding
from mitmproxy.net.http import cookies
from mitmproxy.net.http import multipart
from mitmproxy.net.http import status_codes
from mitmproxy.net.http import url
from mitmproxy.net.http.headers import assemble_content_type
from mitmproxy.net.http.headers import parse_content_type
from mitmproxy.utils import human
from mitmproxy.utils import strutils
from mitmproxy.utils import typecheck
from mitmproxy.utils.strutils import always_bytes
from mitmproxy.utils.strutils import always_str


# While headers _should_ be ASCII, it's not uncommon for certain headers to be utf-8 encoded.
def _native(x: bytes) -> str:
    return x.decode("utf-8", "surrogateescape")


def _always_bytes(x: Union[str, bytes]) -> bytes:
    return strutils.always_bytes(x, "utf-8", "surrogateescape")


# This cannot be easily typed with mypy yet, so we just specify MultiDict without concrete types.
class Headers(multidict.MultiDict):  # type: ignore
    """
    Header class which allows both convenient access to individual headers as well as
    direct access to the underlying raw data. Provides a full dictionary interface.

    Create headers with keyword arguments:
    >>> h = Headers(host="example.com", content_type="application/xml")

    Headers mostly behave like a normal dict:
    >>> h["Host"]
    "example.com"

    Headers are case insensitive:
    >>> h["host"]
    "example.com"

    Headers can also be created from a list of raw (header_name, header_value) byte tuples:
    >>> h = Headers([
        (b"Host",b"example.com"),
        (b"Accept",b"text/html"),
        (b"accept",b"application/xml")
    ])

    Multiple headers are folded into a single header as per RFC 7230:
    >>> h["Accept"]
    "text/html, application/xml"

    Setting a header removes all existing headers with the same name:
    >>> h["Accept"] = "application/text"
    >>> h["Accept"]
    "application/text"

    `bytes(h)` returns an HTTP/1 header block:
    >>> print(bytes(h))
    Host: example.com
    Accept: application/text

    For full control, the raw header fields can be accessed:
    >>> h.fields

    Caveats:
     - For use with the "Set-Cookie" and "Cookie" headers, either use `Response.cookies` or see `Headers.get_all`.
    """

    def __init__(self, fields: Iterable[Tuple[bytes, bytes]] = (), **headers):
        """
        *Args:*
         - *fields:* (optional) list of ``(name, value)`` header byte tuples,
           e.g. ``[(b"Host", b"example.com")]``. All names and values must be bytes.
         - *\*\*headers:* Additional headers to set. Will overwrite existing values from `fields`.
           For convenience, underscores in header names will be transformed to dashes -
           this behaviour does not extend to other methods.

        If ``**headers`` contains multiple keys that have equal ``.lower()`` representations,
        the behavior is undefined.
        """
        super().__init__(fields)

        for key, value in self.fields:
            if not isinstance(key, bytes) or not isinstance(value, bytes):
                raise TypeError("Header fields must be bytes.")

        # content_type -> content-type
        self.update({
            _always_bytes(name).replace(b"_", b"-"): _always_bytes(value)
            for name, value in headers.items()
        })

    fields: Tuple[Tuple[bytes, bytes], ...]

    @staticmethod
    def _reduce_values(values) -> str:
        # Headers can be folded
        return ", ".join(values)

    @staticmethod
    def _kconv(key) -> str:
        # Headers are case-insensitive
        return key.lower()

    def __bytes__(self) -> bytes:
        if self.fields:
            return b"\r\n".join(b": ".join(field) for field in self.fields) + b"\r\n"
        else:
            return b""

    def __delitem__(self, key: Union[str, bytes]) -> None:
        key = _always_bytes(key)
        super().__delitem__(key)

    def __iter__(self) -> Iterator[str]:
        for x in super().__iter__():
            yield _native(x)

    def get_all(self, name: Union[str, bytes]) -> List[str]:
        """
        Like `Headers.get`, but does not fold multiple headers into a single one.
        This is useful for Set-Cookie and Cookie headers, which do not support folding.

        *See also:*
         - <https://tools.ietf.org/html/rfc7230#section-3.2.2>
         - <https://datatracker.ietf.org/doc/html/rfc6265#section-5.4>
         - <https://datatracker.ietf.org/doc/html/rfc7540#section-8.1.2.5>
        """
        name = _always_bytes(name)
        return [
            _native(x) for x in
            super().get_all(name)
        ]

    def set_all(self, name: Union[str, bytes], values: List[Union[str, bytes]]):
        """
        Explicitly set multiple headers for the given key.
        See `Headers.get_all`.
        """
        name = _always_bytes(name)
        values = [_always_bytes(x) for x in values]
        return super().set_all(name, values)

    def insert(self, index: int, key: Union[str, bytes], value: Union[str, bytes]):
        key = _always_bytes(key)
        value = _always_bytes(value)
        super().insert(index, key, value)

    def items(self, multi=False):
        if multi:
            return (
                (_native(k), _native(v))
                for k, v in self.fields
            )
        else:
            return super().items()


@dataclass
class MessageData(serializable.Serializable):
    http_version: bytes
    headers: Headers
    content: Optional[bytes]
    trailers: Optional[Headers]
    timestamp_start: float
    timestamp_end: Optional[float]

    # noinspection PyUnreachableCode
    if __debug__:
        def __post_init__(self):
            for field in fields(self):
                val = getattr(self, field.name)
                typecheck.check_option_type(field.name, val, field.type)

    def set_state(self, state):
        for k, v in state.items():
            if k in ("headers", "trailers") and v is not None:
                v = Headers.from_state(v)
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        state["headers"] = state["headers"].get_state()
        if state["trailers"] is not None:
            state["trailers"] = state["trailers"].get_state()
        return state

    @classmethod
    def from_state(cls, state):
        state["headers"] = Headers.from_state(state["headers"])
        if state["trailers"] is not None:
            state["trailers"] = Headers.from_state(state["trailers"])
        return cls(**state)


@dataclass
class RequestData(MessageData):
    host: str
    port: int
    method: bytes
    scheme: bytes
    authority: bytes
    path: bytes


@dataclass
class ResponseData(MessageData):
    status_code: int
    reason: bytes


class Message(serializable.Serializable):
    """Base class for `Request` and `Response`."""

    @classmethod
    def from_state(cls, state):
        return cls(**state)

    def get_state(self):
        return self.data.get_state()

    def set_state(self, state):
        self.data.set_state(state)

    data: MessageData
    stream: Union[Callable[[bytes], Union[Iterable[bytes], bytes]], bool] = False
    """
    This attribute controls if the message body should be streamed.

    If `False`, mitmproxy will buffer the entire body before forwarding it to the destination.
    This makes it possible to perform string replacements on the entire body.
    If `True`, the message body will not be buffered on the proxy
    but immediately forwarded instead.
    Alternatively, a transformation function can be specified, which will be called for each chunk of data.
    Please note that packet boundaries generally should not be relied upon.

    This attribute must be set in the `requestheaders` or `responseheaders` hook.
    Setting it in `request` or  `response` is already too late, mitmproxy has buffered the message body already.
    """

    @property
    def http_version(self) -> str:
        """
        HTTP version string, for example `HTTP/1.1`.
        """
        return self.data.http_version.decode("utf-8", "surrogateescape")

    @http_version.setter
    def http_version(self, http_version: Union[str, bytes]) -> None:
        self.data.http_version = strutils.always_bytes(http_version, "utf-8", "surrogateescape")

    @property
    def is_http10(self) -> bool:
        return self.data.http_version == b"HTTP/1.0"

    @property
    def is_http11(self) -> bool:
        return self.data.http_version == b"HTTP/1.1"

    @property
    def is_http2(self) -> bool:
        return self.data.http_version == b"HTTP/2.0"

    @property
    def headers(self) -> Headers:
        """
        The HTTP headers.
        """
        return self.data.headers

    @headers.setter
    def headers(self, h: Headers) -> None:
        self.data.headers = h

    @property
    def trailers(self) -> Optional[Headers]:
        """
        The [HTTP trailers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Trailer).
        """
        return self.data.trailers

    @trailers.setter
    def trailers(self, h: Optional[Headers]) -> None:
        self.data.trailers = h

    @property
    def raw_content(self) -> Optional[bytes]:
        """
        The raw (potentially compressed) HTTP message body.

        In contrast to `Message.content` and `Message.text`, accessing this property never raises.

        *See also:* `Message.content`, `Message.text`
        """
        return self.data.content

    @raw_content.setter
    def raw_content(self, content: Optional[bytes]) -> None:
        self.data.content = content

    @property
    def content(self) -> Optional[bytes]:
        """
        The uncompressed HTTP message body as bytes.

        Accessing this attribute may raise a `ValueError` when the HTTP content-encoding is invalid.

        *See also:* `Message.raw_content`, `Message.text`
        """
        return self.get_content()

    @content.setter
    def content(self, value: Optional[bytes]) -> None:
        self.set_content(value)

    @property
    def text(self) -> Optional[str]:
        """
        The uncompressed and decoded HTTP message body as text.

        Accessing this attribute may raise a `ValueError` when either content-encoding or charset is invalid.

        *See also:* `Message.raw_content`, `Message.content`
        """
        return self.get_text()

    @text.setter
    def text(self, value: Optional[str]) -> None:
        self.set_text(value)

    def set_content(self, value: Optional[bytes]) -> None:
        if value is None:
            self.raw_content = None
            return
        if not isinstance(value, bytes):
            raise TypeError(
                f"Message content must be bytes, not {type(value).__name__}. "
                "Please use .text if you want to assign a str."
            )
        ce = self.headers.get("content-encoding")
        try:
            self.raw_content = encoding.encode(value, ce or "identity")
        except ValueError:
            # So we have an invalid content-encoding?
            # Let's remove it!
            del self.headers["content-encoding"]
            self.raw_content = value

        if "transfer-encoding" in self.headers:
            # https://httpwg.org/specs/rfc7230.html#header.content-length
            # don't set content-length if a transfer-encoding is provided
            pass
        else:
            self.headers["content-length"] = str(len(self.raw_content))

    def get_content(self, strict: bool = True) -> Optional[bytes]:
        """
        Similar to `Message.content`, but does not raise if `strict` is `False`.
        Instead, the compressed message body is returned as-is.
        """
        if self.raw_content is None:
            return None
        ce = self.headers.get("content-encoding")
        if ce:
            try:
                content = encoding.decode(self.raw_content, ce)
                # A client may illegally specify a byte -> str encoding here (e.g. utf8)
                if isinstance(content, str):
                    raise ValueError(f"Invalid Content-Encoding: {ce}")
                return content
            except ValueError:
                if strict:
                    raise
                return self.raw_content
        else:
            return self.raw_content

    def _get_content_type_charset(self) -> Optional[str]:
        ct = parse_content_type(self.headers.get("content-type", ""))
        if ct:
            return ct[2].get("charset")
        return None

    def _guess_encoding(self, content: bytes = b"") -> str:
        enc = self._get_content_type_charset()
        if not enc:
            if "json" in self.headers.get("content-type", ""):
                enc = "utf8"
        if not enc:
            meta_charset = re.search(rb"""<meta[^>]+charset=['"]?([^'">]+)""", content)
            if meta_charset:
                enc = meta_charset.group(1).decode("ascii", "ignore")
        if not enc:
            if "text/css" in self.headers.get("content-type", ""):
                # @charset rule must be the very first thing.
                css_charset = re.match(rb"""@charset "([^"]+)";""", content)
                if css_charset:
                    enc = css_charset.group(1).decode("ascii", "ignore")
        if not enc:
            enc = "latin-1"
        # Use GB 18030 as the superset of GB2312 and GBK to fix common encoding problems on Chinese websites.
        if enc.lower() in ("gb2312", "gbk"):
            enc = "gb18030"

        return enc

    def set_text(self, text: Optional[str]) -> None:
        if text is None:
            self.content = None
            return
        enc = self._guess_encoding()

        try:
            self.content = cast(bytes, encoding.encode(text, enc))
        except ValueError:
            # Fall back to UTF-8 and update the content-type header.
            ct = parse_content_type(self.headers.get("content-type", "")) or ("text", "plain", {})
            ct[2]["charset"] = "utf-8"
            self.headers["content-type"] = assemble_content_type(*ct)
            enc = "utf8"
            self.content = text.encode(enc, "surrogateescape")

    def get_text(self, strict: bool = True) -> Optional[str]:
        """
        Similar to `Message.text`, but does not raise if `strict` is `False`.
        Instead, the message body is returned as surrogate-escaped UTF-8.
        """
        content = self.get_content(strict)
        if content is None:
            return None
        enc = self._guess_encoding(content)
        try:
            return cast(str, encoding.decode(content, enc))
        except ValueError:
            if strict:
                raise
            return content.decode("utf8", "surrogateescape")

    @property
    def timestamp_start(self) -> float:
        """
        *Timestamp:* Headers received.
        """
        return self.data.timestamp_start

    @timestamp_start.setter
    def timestamp_start(self, timestamp_start: float) -> None:
        self.data.timestamp_start = timestamp_start

    @property
    def timestamp_end(self) -> Optional[float]:
        """
        *Timestamp:* Last byte received.
        """
        return self.data.timestamp_end

    @timestamp_end.setter
    def timestamp_end(self, timestamp_end: Optional[float]):
        self.data.timestamp_end = timestamp_end

    def decode(self, strict: bool = True) -> None:
        """
        Decodes body based on the current Content-Encoding header, then
        removes the header. If there is no Content-Encoding header, no
        action is taken.

        *Raises:*
         - `ValueError`, when the content-encoding is invalid and strict is True.
        """
        decoded = self.get_content(strict)
        self.headers.pop("content-encoding", None)
        self.content = decoded

    def encode(self, encoding: str) -> None:
        """
        Encodes body with the given encoding, where e is "gzip", "deflate", "identity", "br", or "zstd".
        Any existing content-encodings are overwritten, the content is not decoded beforehand.

        *Raises:*
         - `ValueError`, when the specified content-encoding is invalid.
        """
        self.headers["content-encoding"] = encoding
        self.content = self.raw_content
        if "content-encoding" not in self.headers:
            raise ValueError("Invalid content encoding {}".format(repr(encoding)))

    def json(self, **kwargs: Any) -> Any:
        """
        Returns the JSON encoded content of the response, if any.
        `**kwargs` are optional arguments that will be
        passed to `json.loads()`.

        Will raise if the content can not be decoded and then parsed as JSON.

        *Raises:*
         - `json.decoder.JSONDecodeError` if content is not valid JSON.
         - `TypeError` if the content is not available, for example because the response
            has been streamed.
        """
        content = self.get_content(strict=False)
        if content is None:
            raise TypeError('Message content is not available.')
        else:
            return json.loads(content, **kwargs)


class Request(Message):
    """
    An HTTP request.
    """
    data: RequestData

    def __init__(
        self,
        host: str,
        port: int,
        method: bytes,
        scheme: bytes,
        authority: bytes,
        path: bytes,
        http_version: bytes,
        headers: Union[Headers, Tuple[Tuple[bytes, bytes], ...]],
        content: Optional[bytes],
        trailers: Union[Headers, Tuple[Tuple[bytes, bytes], ...], None],
        timestamp_start: float,
        timestamp_end: Optional[float],
    ):
        # auto-convert invalid types to retain compatibility with older code.
        if isinstance(host, bytes):
            host = host.decode("idna", "strict")
        if isinstance(method, str):
            method = method.encode("ascii", "strict")
        if isinstance(scheme, str):
            scheme = scheme.encode("ascii", "strict")
        if isinstance(authority, str):
            authority = authority.encode("ascii", "strict")
        if isinstance(path, str):
            path = path.encode("ascii", "strict")
        if isinstance(http_version, str):
            http_version = http_version.encode("ascii", "strict")

        if isinstance(content, str):
            raise ValueError(f"Content must be bytes, not {type(content).__name__}")
        if not isinstance(headers, Headers):
            headers = Headers(headers)
        if trailers is not None and not isinstance(trailers, Headers):
            trailers = Headers(trailers)

        self.data = RequestData(
            host=host,
            port=port,
            method=method,
            scheme=scheme,
            authority=authority,
            path=path,
            http_version=http_version,
            headers=headers,
            content=content,
            trailers=trailers,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

    def __repr__(self) -> str:
        if self.host and self.port:
            hostport = f"{self.host}:{self.port}"
        else:
            hostport = ""
        path = self.path or ""
        return f"Request({self.method} {hostport}{path})"

    @classmethod
    def make(
        cls,
        method: str,
        url: str,
        content: Union[bytes, str] = "",
        headers: Union[Headers, Dict[Union[str, bytes], Union[str, bytes]], Iterable[Tuple[bytes, bytes]]] = ()
    ) -> "Request":
        """
        Simplified API for creating request objects.
        """
        # Headers can be list or dict, we differentiate here.
        if isinstance(headers, Headers):
            pass
        elif isinstance(headers, dict):
            headers = Headers(
                (always_bytes(k, "utf-8", "surrogateescape"),
                 always_bytes(v, "utf-8", "surrogateescape"))
                for k, v in headers.items()
            )
        elif isinstance(headers, Iterable):
            headers = Headers(headers)  # type: ignore
        else:
            raise TypeError("Expected headers to be an iterable or dict, but is {}.".format(
                type(headers).__name__
            ))

        req = cls(
            "",
            0,
            method.encode("utf-8", "surrogateescape"),
            b"",
            b"",
            b"",
            b"HTTP/1.1",
            headers,
            b"",
            None,
            time.time(),
            time.time(),
        )

        req.url = url
        # Assign this manually to update the content-length header.
        if isinstance(content, bytes):
            req.content = content
        elif isinstance(content, str):
            req.text = content
        else:
            raise TypeError(f"Expected content to be str or bytes, but is {type(content).__name__}.")

        return req

    @property
    def first_line_format(self) -> str:
        """
        *Read-only:* HTTP request form as defined in [RFC 7230](https://tools.ietf.org/html/rfc7230#section-5.3).

        origin-form and asterisk-form are subsumed as "relative".
        """
        if self.method == "CONNECT":
            return "authority"
        elif self.authority:
            return "absolute"
        else:
            return "relative"

    @property
    def method(self) -> str:
        """
        HTTP request method, e.g. "GET".
        """
        return self.data.method.decode("utf-8", "surrogateescape").upper()

    @method.setter
    def method(self, val: Union[str, bytes]) -> None:
        self.data.method = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def scheme(self) -> str:
        """
        HTTP request scheme, which should be "http" or "https".
        """
        return self.data.scheme.decode("utf-8", "surrogateescape")

    @scheme.setter
    def scheme(self, val: Union[str, bytes]) -> None:
        self.data.scheme = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def authority(self) -> str:
        """
        HTTP request authority.

        For HTTP/1, this is the authority portion of the request target
        (in either absolute-form or authority-form).
        For origin-form and asterisk-form requests, this property is set to an empty string.

        For HTTP/2, this is the :authority pseudo header.

        *See also:* `Request.host`, `Request.host_header`, `Request.pretty_host`
        """
        try:
            return self.data.authority.decode("idna")
        except UnicodeError:
            return self.data.authority.decode("utf8", "surrogateescape")

    @authority.setter
    def authority(self, val: Union[str, bytes]) -> None:
        if isinstance(val, str):
            try:
                val = val.encode("idna", "strict")
            except UnicodeError:
                val = val.encode("utf8", "surrogateescape")  # type: ignore
        self.data.authority = val

    @property
    def host(self) -> str:
        """
        Target server for this request. This may be parsed from the raw request
        (e.g. from a ``GET http://example.com/ HTTP/1.1`` request line)
        or inferred from the proxy mode (e.g. an IP in transparent mode).

        Setting the host attribute also updates the host header and authority information, if present.

        *See also:* `Request.authority`, `Request.host_header`, `Request.pretty_host`
        """
        return self.data.host

    @host.setter
    def host(self, val: Union[str, bytes]) -> None:
        self.data.host = always_str(val, "idna", "strict")

        # Update host header
        if "Host" in self.data.headers:
            self.data.headers["Host"] = val
        # Update authority
        if self.data.authority:
            self.authority = url.hostport(self.scheme, self.host, self.port)

    @property
    def host_header(self) -> Optional[str]:
        """
        The request's host/authority header.

        This property maps to either ``request.headers["Host"]`` or
        ``request.authority``, depending on whether it's HTTP/1.x or HTTP/2.0.

        *See also:* `Request.authority`,`Request.host`, `Request.pretty_host`
        """
        if self.is_http2:
            return self.authority or self.data.headers.get("Host", None)
        else:
            return self.data.headers.get("Host", None)

    @host_header.setter
    def host_header(self, val: Union[None, str, bytes]) -> None:
        if val is None:
            if self.is_http2:
                self.data.authority = b""
            self.headers.pop("Host", None)
        else:
            if self.is_http2:
                self.authority = val  # type: ignore
            if not self.is_http2 or "Host" in self.headers:
                # For h2, we only overwrite, but not create, as :authority is the h2 host header.
                self.headers["Host"] = val

    @property
    def port(self) -> int:
        """
        Target port.
        """
        return self.data.port

    @port.setter
    def port(self, port: int) -> None:
        self.data.port = port

    @property
    def path(self) -> str:
        """
        HTTP request path, e.g. "/index.html".
        Usually starts with a slash, except for OPTIONS requests, which may just be "*".
        """
        return self.data.path.decode("utf-8", "surrogateescape")

    @path.setter
    def path(self, val: Union[str, bytes]) -> None:
        self.data.path = always_bytes(val, "utf-8", "surrogateescape")

    @property
    def url(self) -> str:
        """
        The full URL string, constructed from `Request.scheme`, `Request.host`, `Request.port` and `Request.path`.

        Settings this property updates these attributes as well.
        """
        if self.first_line_format == "authority":
            return f"{self.host}:{self.port}"
        return url.unparse(self.scheme, self.host, self.port, self.path)

    @url.setter
    def url(self, val: Union[str, bytes]) -> None:
        val = always_str(val, "utf-8", "surrogateescape")
        self.scheme, self.host, self.port, self.path = url.parse(val)

    @property
    def pretty_host(self) -> str:
        """
        *Read-only:* Like `Request.host`, but using `Request.host_header` header as an additional (preferred) data source.
        This is useful in transparent mode where `Request.host` is only an IP address.

        *Warning:* When working in adversarial environments, this may not reflect the actual destination
        as the Host header could be spoofed.
        """
        authority = self.host_header
        if authority:
            return url.parse_authority(authority, check=False)[0]
        else:
            return self.host

    @property
    def pretty_url(self) -> str:
        """
        *Read-only:* Like `Request.url`, but using `Request.pretty_host` instead of `Request.host`.
        """
        if self.first_line_format == "authority":
            return self.authority

        host_header = self.host_header
        if not host_header:
            return self.url

        pretty_host, pretty_port = url.parse_authority(host_header, check=False)
        pretty_port = pretty_port or url.default_port(self.scheme) or 443

        return url.unparse(self.scheme, pretty_host, pretty_port, self.path)

    def _get_query(self):
        query = urllib.parse.urlparse(self.url).query
        return tuple(url.decode(query))

    def _set_query(self, query_data):
        query = url.encode(query_data)
        _, _, path, params, _, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

    @property
    def query(self) -> multidict.MultiDictView[str, str]:
        """
        The request query as a mutable mapping view on the request's path.
        For the most part, this behaves like a dictionary.
        Modifications to the MultiDictView update `Request.path`, and vice versa.
        """
        return multidict.MultiDictView(
            self._get_query,
            self._set_query
        )

    @query.setter
    def query(self, value):
        self._set_query(value)

    def _get_cookies(self):
        h = self.headers.get_all("Cookie")
        return tuple(cookies.parse_cookie_headers(h))

    def _set_cookies(self, value):
        self.headers["cookie"] = cookies.format_cookie_header(value)

    @property
    def cookies(self) -> multidict.MultiDictView[str, str]:
        """
        The request cookies.
        For the most part, this behaves like a dictionary.
        Modifications to the MultiDictView update `Request.headers`, and vice versa.
        """
        return multidict.MultiDictView(
            self._get_cookies,
            self._set_cookies
        )

    @cookies.setter
    def cookies(self, value):
        self._set_cookies(value)

    @property
    def path_components(self) -> Tuple[str, ...]:
        """
        The URL's path components as a tuple of strings.
        Components are unquoted.
        """
        path = urllib.parse.urlparse(self.url).path
        # This needs to be a tuple so that it's immutable.
        # Otherwise, this would fail silently:
        #   request.path_components.append("foo")
        return tuple(url.unquote(i) for i in path.split("/") if i)

    @path_components.setter
    def path_components(self, components: Iterable[str]):
        components = map(lambda x: url.quote(x, safe=""), components)
        path = "/" + "/".join(components)
        _, _, _, params, query, fragment = urllib.parse.urlparse(self.url)
        self.path = urllib.parse.urlunparse(["", "", path, params, query, fragment])

    def anticache(self) -> None:
        """
        Modifies this request to remove headers that might produce a cached response.
        """
        delheaders = (
            "if-modified-since",
            "if-none-match",
        )
        for i in delheaders:
            self.headers.pop(i, None)

    def anticomp(self) -> None:
        """
        Modify the Accept-Encoding header to only accept uncompressed responses.
        """
        self.headers["accept-encoding"] = "identity"

    def constrain_encoding(self) -> None:
        """
        Limits the permissible Accept-Encoding values, based on what we can decode appropriately.
        """
        accept_encoding = self.headers.get("accept-encoding")
        if accept_encoding:
            self.headers["accept-encoding"] = (
                ', '.join(
                    e
                    for e in {"gzip", "identity", "deflate", "br", "zstd"}
                    if e in accept_encoding
                )
            )

    def _get_urlencoded_form(self):
        is_valid_content_type = "application/x-www-form-urlencoded" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            return tuple(url.decode(self.get_text(strict=False)))
        return ()

    def _set_urlencoded_form(self, form_data):
        """
        Sets the body to the URL-encoded form data, and adds the appropriate content-type header.
        This will overwrite the existing content if there is one.
        """
        self.headers["content-type"] = "application/x-www-form-urlencoded"
        self.content = url.encode(form_data, self.get_text(strict=False)).encode()

    @property
    def urlencoded_form(self) -> multidict.MultiDictView[str, str]:
        """
        The URL-encoded form data.

        If the content-type indicates non-form data or the form could not be parsed, this is set to
        an empty `MultiDictView`.

        Modifications to the MultiDictView update `Request.content`, and vice versa.
        """
        return multidict.MultiDictView(
            self._get_urlencoded_form,
            self._set_urlencoded_form
        )

    @urlencoded_form.setter
    def urlencoded_form(self, value):
        self._set_urlencoded_form(value)

    def _get_multipart_form(self):
        is_valid_content_type = "multipart/form-data" in self.headers.get("content-type", "").lower()
        if is_valid_content_type:
            try:
                return multipart.decode(self.headers.get("content-type"), self.content)
            except ValueError:
                pass
        return ()

    def _set_multipart_form(self, value):
        is_valid_content_type = self.headers.get("content-type", "").lower().startswith("multipart/form-data")
        if not is_valid_content_type:
            """
            Generate a random boundary here.

            See <https://datatracker.ietf.org/doc/html/rfc2046#section-5.1.1> for specifications
            on generating the boundary.
            """
            boundary = "-" * 20 + binascii.hexlify(os.urandom(16)).decode()
            self.headers["content-type"] = f"multipart/form-data; boundary={boundary}"
        self.content = multipart.encode(self.headers, value)

    @property
    def multipart_form(self) -> multidict.MultiDictView[bytes, bytes]:
        """
        The multipart form data.

        If the content-type indicates non-form data or the form could not be parsed, this is set to
        an empty `MultiDictView`.

        Modifications to the MultiDictView update `Request.content`, and vice versa.
        """
        return multidict.MultiDictView(
            self._get_multipart_form,
            self._set_multipart_form
        )

    @multipart_form.setter
    def multipart_form(self, value):
        self._set_multipart_form(value)


class Response(Message):
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
                (always_bytes(k, "utf-8", "surrogateescape"),  # type: ignore
                 always_bytes(v, "utf-8", "surrogateescape"))
                for k, v in headers.items()
            )
        elif isinstance(headers, Iterable):
            headers = Headers(headers)  # type: ignore
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
        HTTP reason phrase, for example "Not Found".

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
    def cookies(self) -> multidict.MultiDictView[str, Tuple[str, multidict.MultiDict[str, Optional[str]]]]:
        """
        The response cookies. A possibly empty `MultiDictView`, where the keys are cookie
        name strings, and values are `(cookie value, attributes)` tuples. Within
        attributes, unary attributes (e.g. `HTTPOnly`) are indicated by a `None` value.
        Modifications to the MultiDictView update `Response.headers`, and vice versa.

        *Warning:* Changes to `attributes` will not be picked up unless you also reassign
        the `(cookie value, attributes)` tuple directly in the `MultiDictView`.
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

         - It adjusts date, expires, and last-modified headers.
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


class HTTPFlow(flow.Flow):
    """
    An HTTPFlow is a collection of objects representing a single HTTP
    transaction.
    """
    request: Request
    """The client's HTTP request."""
    response: Optional[Response] = None
    """The server's HTTP response."""
    error: Optional[flow.Error] = None
    """
    A connection or protocol error affecting this flow.

    Note that it's possible for a Flow to have both a response and an error
    object. This might happen, for instance, when a response was received
    from the server, but there was an error sending it back to the client.
    """

    websocket: Optional[WebSocketData] = None
    """
    If this HTTP flow initiated a WebSocket connection, this attribute contains all associated WebSocket data.
    """

    def __init__(self, client_conn, server_conn, live=None, mode="regular"):
        super().__init__("http", client_conn, server_conn, live)
        self.mode = mode

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    # mypy doesn't support update with kwargs
    _stateobject_attributes.update(dict(
        request=Request,
        response=Response,
        websocket=WebSocketData,
        mode=str
    ))

    def __repr__(self):
        s = "<HTTPFlow"
        for a in ("request", "response", "websocket", "error", "client_conn", "server_conn"):
            if getattr(self, a, False):
                s += f"\r\n  {a} = {{flow.{a}}}"
        s += ">"
        return s.format(flow=self)

    @property
    def timestamp_start(self) -> float:
        """*Read-only:* An alias for `Request.timestamp_start`."""
        return self.request.timestamp_start

    def copy(self):
        f = super().copy()
        if self.request:
            f.request = self.request.copy()
        if self.response:
            f.response = self.response.copy()
        return f


__all__ = [
    "HTTPFlow",
    "Message",
    "Request",
    "Response",
    "Headers",
]
