import re
from typing import Optional  # noqa

from mitmproxy.utils import strutils
from mitmproxy.net.http import encoding
from mitmproxy.coretypes import serializable
from mitmproxy.net.http import headers as mheaders


class MessageData(serializable.Serializable):
    headers: mheaders.Headers
    content: bytes
    http_version: bytes
    timestamp_start: float
    timestamp_end: float

    def __eq__(self, other):
        if isinstance(other, MessageData):
            return self.__dict__ == other.__dict__
        return False

    def set_state(self, state):
        for k, v in state.items():
            if k == "headers":
                v = mheaders.Headers.from_state(v)
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        state["headers"] = state["headers"].get_state()
        if 'trailers' in state and state["trailers"] is not None:
            state["trailers"] = state["trailers"].get_state()
        return state

    @classmethod
    def from_state(cls, state):
        state["headers"] = mheaders.Headers.from_state(state["headers"])
        return cls(**state)


class Message(serializable.Serializable):
    data: MessageData

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.data == other.data
        return False

    def get_state(self):
        return self.data.get_state()

    def set_state(self, state):
        self.data.set_state(state)

    @classmethod
    def from_state(cls, state):
        state["headers"] = mheaders.Headers.from_state(state["headers"])
        if 'trailers' in state and state["trailers"] is not None:
            state["trailers"] = mheaders.Headers.from_state(state["trailers"])
        return cls(**state)

    @property
    def headers(self):
        """
        Message headers object

        Returns:
            mitmproxy.net.http.Headers
        """
        return self.data.headers

    @headers.setter
    def headers(self, h):
        self.data.headers = h

    @property
    def raw_content(self) -> bytes:
        """
        The raw (potentially compressed) HTTP message body as bytes.

        See also: :py:attr:`content`, :py:class:`text`
        """
        return self.data.content

    @raw_content.setter
    def raw_content(self, content):
        self.data.content = content

    def get_content(self, strict: bool=True) -> Optional[bytes]:
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
                    raise ValueError("Invalid Content-Encoding: {}".format(ce))
                return content
            except ValueError:
                if strict:
                    raise
                return self.raw_content
        else:
            return self.raw_content

    def set_content(self, value):
        if value is None:
            self.raw_content = None
            return
        if not isinstance(value, bytes):
            raise TypeError(
                "Message content must be bytes, not {}. "
                "Please use .text if you want to assign a str."
                .format(type(value).__name__)
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
    def trailers(self):
        """
        Message trailers object

        Returns:
            mitmproxy.net.http.Headers
        """
        return self.data.trailers

    @trailers.setter
    def trailers(self, h):
        self.data.trailers = h

    @property
    def http_version(self):
        """
        Version string, e.g. "HTTP/1.1"
        """
        return self.data.http_version.decode("utf-8", "surrogateescape")

    @http_version.setter
    def http_version(self, http_version):
        self.data.http_version = strutils.always_bytes(http_version, "utf-8", "surrogateescape")

    @property
    def timestamp_start(self):
        """
        First byte timestamp
        """
        return self.data.timestamp_start

    @timestamp_start.setter
    def timestamp_start(self, timestamp_start):
        self.data.timestamp_start = timestamp_start

    @property
    def timestamp_end(self):
        """
        Last byte timestamp
        """
        return self.data.timestamp_end

    @timestamp_end.setter
    def timestamp_end(self, timestamp_end):
        self.data.timestamp_end = timestamp_end

    def _get_content_type_charset(self) -> Optional[str]:
        ct = mheaders.parse_content_type(self.headers.get("content-type", ""))
        if ct:
            return ct[2].get("charset")
        return None

    def _guess_encoding(self, content=b"") -> str:
        enc = self._get_content_type_charset()
        if not enc:
            if "json" in self.headers.get("content-type", ""):
                enc = "utf8"
        if not enc:
            meta_charset = re.search(rb"""<meta[^>]+charset=['"]?([^'">]+)""", content)
            if meta_charset:
                enc = meta_charset.group(1).decode("ascii", "ignore")
        if not enc:
            enc = "latin-1"
        # Use GB 18030 as the superset of GB2312 and GBK to fix common encoding problems on Chinese websites.
        if enc.lower() in ("gb2312", "gbk"):
            enc = "gb18030"

        return enc

    def get_text(self, strict: bool=True) -> Optional[str]:
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
            return encoding.decode(content, enc)
        except ValueError:
            if strict:
                raise
            return content.decode("utf8", "surrogateescape")

    def set_text(self, text):
        if text is None:
            self.content = None
            return
        enc = self._guess_encoding()

        try:
            self.content = encoding.encode(text, enc)
        except ValueError:
            # Fall back to UTF-8 and update the content-type header.
            ct = mheaders.parse_content_type(self.headers.get("content-type", "")) or ("text", "plain", {})
            ct[2]["charset"] = "utf-8"
            self.headers["content-type"] = mheaders.assemble_content_type(*ct)
            enc = "utf8"
            self.content = text.encode(enc, "surrogateescape")

    text = property(get_text, set_text)

    def decode(self, strict=True):
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

    def encode(self, e):
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
