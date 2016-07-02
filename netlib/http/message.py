from __future__ import absolute_import, print_function, division

import re
import warnings

import six

from netlib import encoding, strutils, basetypes
from netlib.http import headers

if six.PY2:  # pragma: no cover
    def _native(x):
        return x

    def _always_bytes(x):
        return x
else:
    # While headers _should_ be ASCII, it's not uncommon for certain headers to be utf-8 encoded.
    def _native(x):
        return x.decode("utf-8", "surrogateescape")

    def _always_bytes(x):
        return strutils.always_bytes(x, "utf-8", "surrogateescape")


class MessageData(basetypes.Serializable):
    def __eq__(self, other):
        if isinstance(other, MessageData):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(frozenset(self.__dict__.items()))

    def set_state(self, state):
        for k, v in state.items():
            if k == "headers":
                v = headers.Headers.from_state(v)
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        state["headers"] = state["headers"].get_state()
        return state

    @classmethod
    def from_state(cls, state):
        state["headers"] = headers.Headers.from_state(state["headers"])
        return cls(**state)


class CachedDecode(object):
    __slots__ = ["encoded", "encoding", "decoded"]

    def __init__(self, object, encoding, decoded):
        self.encoded = object
        self.encoding = encoding
        self.decoded = decoded

no_cached_decode = CachedDecode(None, None, None)


class Message(basetypes.Serializable):
    def __init__(self):
        self._content_cache = no_cached_decode  # type: CachedDecode
        self._text_cache = no_cached_decode  # type: CachedDecode

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.data == other.data
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.data) ^ 1

    def get_state(self):
        return self.data.get_state()

    def set_state(self, state):
        self.data.set_state(state)

    @classmethod
    def from_state(cls, state):
        state["headers"] = headers.Headers.from_state(state["headers"])
        return cls(**state)

    @property
    def headers(self):
        """
        Message headers object

        Returns:
            netlib.http.Headers
        """
        return self.data.headers

    @headers.setter
    def headers(self, h):
        self.data.headers = h

    @property
    def raw_content(self):
        # type: () -> bytes
        """
        The raw (encoded) HTTP message body

        See also: :py:attr:`content`, :py:class:`text`
        """
        return self.data.content

    @raw_content.setter
    def raw_content(self, content):
        self.data.content = content

    @property
    def content(self):
        # type: () -> bytes
        """
        The HTTP message body decoded with the content-encoding header (e.g. gzip)

        See also: :py:class:`raw_content`, :py:attr:`text`
        """
        ce = self.headers.get("content-encoding")
        cached = (
            self._content_cache.encoded == self.raw_content and
            self._content_cache.encoding == ce
        )
        if not cached:
            try:
                if not ce:
                    raise ValueError()
                decoded = encoding.decode(self.raw_content, ce)
            except ValueError:
                decoded = self.raw_content
            self._content_cache = CachedDecode(self.raw_content, ce, decoded)
        return self._content_cache.decoded

    @content.setter
    def content(self, value):
        ce = self.headers.get("content-encoding")
        cached = (
            self._content_cache.decoded == value and
            self._content_cache.encoding == ce
        )
        if not cached:
            try:
                if not ce:
                    raise ValueError()
                encoded = encoding.encode(value, ce)
            except ValueError:
                # Do we have an unknown content-encoding?
                # If so, we want to remove it.
                if value and ce:
                    self.headers.pop("content-encoding", None)
                    ce = None
                encoded = value
            self._content_cache = CachedDecode(encoded, ce, value)
        self.raw_content = self._content_cache.encoded
        if isinstance(self.raw_content, bytes):
            self.headers["content-length"] = str(len(self.raw_content))

    @property
    def http_version(self):
        """
        Version string, e.g. "HTTP/1.1"
        """
        return _native(self.data.http_version)

    @http_version.setter
    def http_version(self, http_version):
        self.data.http_version = _always_bytes(http_version)

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

    def _get_content_type_charset(self):
        # type: () -> Optional[str]
        ct = headers.parse_content_type(self.headers.get("content-type", ""))
        if ct:
            return ct[2].get("charset")

    @property
    def text(self):
        # type: () -> six.text_type
        """
        The HTTP message body decoded with both content-encoding header (e.g. gzip)
        and content-type header charset.

        See also: :py:attr:`content`, :py:class:`raw_content`
        """
        # This attribute should be called text, because that's what requests does.
        enc = self._get_content_type_charset()

        # We may also want to check for HTML meta tags here at some point.

        cached = (
            self._text_cache.encoded == self.content and
            self._text_cache.encoding == enc
        )
        if not cached:
            try:
                if not enc:
                    raise ValueError()
                decoded = encoding.decode(self.content, enc)
            except ValueError:
                decoded = self.content.decode("utf8", "replace" if six.PY2 else "surrogateescape")
            self._text_cache = CachedDecode(self.content, enc, decoded)
        return self._text_cache.decoded

    @text.setter
    def text(self, text):
        enc = self._get_content_type_charset()
        cached = (
            self._text_cache.decoded == text and
            self._text_cache.encoding == enc
        )
        if not cached:
            try:
                if not enc:
                    raise ValueError()
                encoded = encoding.encode(text, enc)
            except ValueError:
                # Do we have an unknown content-type charset?
                # If so, we want to replace it with utf8.
                if text and enc:
                    self.headers["content-type"] = re.sub(
                        "charset=[^;]+",
                        "charset=utf-8",
                        self.headers["content-type"]
                    )
                encoded = text.encode("utf8", "replace" if six.PY2 else "surrogateescape")
            self._text_cache = CachedDecode(encoded, enc, text)
        self.content = self._text_cache.encoded

    def decode(self):
        """
        Decodes body based on the current Content-Encoding header, then
        removes the header. If there is no Content-Encoding header, no
        action is taken.
        """
        self.raw_content = self.content
        self.headers.pop("content-encoding", None)

    def encode(self, e):
        """
        Encodes body with the encoding e, where e is "gzip", "deflate" or "identity".
        """
        self.decode()  # remove the current encoding
        self.headers["content-encoding"] = e
        self.content = self.raw_content

    def replace(self, pattern, repl, flags=0):
        """
        Replaces a regular expression pattern with repl in both the headers
        and the body of the message. Encoded body will be decoded
        before replacement, and re-encoded afterwards.

        Returns:
            The number of replacements made.
        """
        if isinstance(pattern, six.text_type):
            pattern = strutils.escaped_str_to_bytes(pattern)
        if isinstance(repl, six.text_type):
            repl = strutils.escaped_str_to_bytes(repl)
        replacements = 0
        if self.content:
            self.content, replacements = re.subn(
                pattern, repl, self.content, flags=flags
            )
        replacements += self.headers.replace(pattern, repl, flags)
        return replacements

    # Legacy

    @property
    def body(self):  # pragma: no cover
        warnings.warn(".body is deprecated, use .content instead.", DeprecationWarning)
        return self.content

    @body.setter
    def body(self, body):  # pragma: no cover
        warnings.warn(".body is deprecated, use .content instead.", DeprecationWarning)
        self.content = body


class decoded(object):
    """
    Deprecated: You can now directly use :py:attr:`content`.
    :py:attr:`raw_content` has the encoded content.
    """

    def __init__(self, message):
        warnings.warn("decoded() is deprecated, you can now directly use .content instead. "
                      ".raw_content has the encoded content.", DeprecationWarning)

    def __enter__(self):
        pass

    def __exit__(self, type, value, tb):
        pass
