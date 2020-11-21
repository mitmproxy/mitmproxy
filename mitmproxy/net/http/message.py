import re
from dataclasses import dataclass, fields
from typing import Callable, Optional, Union, cast

from mitmproxy.coretypes import serializable
from mitmproxy.net.http import encoding
from mitmproxy.net.http.headers import Headers, assemble_content_type, parse_content_type
from mitmproxy.utils import strutils, typecheck


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


class Message(serializable.Serializable):
    @classmethod
    def from_state(cls, state):
        return cls(**state)

    def get_state(self):
        return self.data.get_state()

    def set_state(self, state):
        self.data.set_state(state)

    data: MessageData
    stream: Union[Callable, bool] = False

    @property
    def http_version(self) -> str:
        """
        Version string, e.g. "HTTP/1.1"
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
        The HTTP trailers.
        """
        return self.data.trailers

    @trailers.setter
    def trailers(self, h: Optional[Headers]) -> None:
        self.data.trailers = h

    @property
    def raw_content(self) -> Optional[bytes]:
        """
        The raw (potentially compressed) HTTP message body as bytes.

        See also: :py:attr:`content`, :py:class:`text`
        """
        return self.data.content

    @raw_content.setter
    def raw_content(self, content: Optional[bytes]) -> None:
        self.data.content = content

    def get_content(self, strict: bool = True) -> Optional[bytes]:
        """
        The uncompressed HTTP message body as bytes.

        Raises:
            ValueError, when the HTTP content-encoding is invalid and strict is True.

        See also: :py:class:`raw_content`, :py:attr:`text`
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
        self.headers["content-length"] = str(len(self.raw_content))

    content = property(get_content, set_content)

    @property
    def timestamp_start(self) -> float:
        """
        First byte timestamp
        """
        return self.data.timestamp_start

    @timestamp_start.setter
    def timestamp_start(self, timestamp_start: float) -> None:
        self.data.timestamp_start = timestamp_start

    @property
    def timestamp_end(self) -> Optional[float]:
        """
        Last byte timestamp
        """
        return self.data.timestamp_end

    @timestamp_end.setter
    def timestamp_end(self, timestamp_end: Optional[float]):
        self.data.timestamp_end = timestamp_end

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

    def get_text(self, strict: bool = True) -> Optional[str]:
        """
        The uncompressed and decoded HTTP message body as text.

        Raises:
            ValueError, when either content-encoding or charset is invalid and strict is True.

        See also: :py:attr:`content`, :py:class:`raw_content`
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

    def set_text(self, text: Optional[str]) -> None:
        if text is None:
            self.content = None
            return
        enc = self._guess_encoding()

        try:
            self.content = encoding.encode(text, enc)
        except ValueError:
            # Fall back to UTF-8 and update the content-type header.
            ct = parse_content_type(self.headers.get("content-type", "")) or ("text", "plain", {})
            ct[2]["charset"] = "utf-8"
            self.headers["content-type"] = assemble_content_type(*ct)
            enc = "utf8"
            self.content = text.encode(enc, "surrogateescape")

    text = property(get_text, set_text)

    def decode(self, strict: bool = True) -> None:
        """
        Decodes body based on the current Content-Encoding header, then
        removes the header. If there is no Content-Encoding header, no
        action is taken.

        Raises:
            ValueError, when the content-encoding is invalid and strict is True.
        """
        decoded = self.get_content(strict)
        self.headers.pop("content-encoding", None)
        self.content = decoded

    def encode(self, e: str) -> None:
        """
        Encodes body with the encoding e, where e is "gzip", "deflate", "identity", "br", or "zstd".
        Any existing content-encodings are overwritten,
        the content is not decoded beforehand.

        Raises:
            ValueError, when the specified content-encoding is invalid.
        """
        self.headers["content-encoding"] = e
        self.content = self.raw_content
        if "content-encoding" not in self.headers:
            raise ValueError("Invalid content encoding {}".format(repr(e)))
