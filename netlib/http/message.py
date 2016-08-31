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


class Message(basetypes.Serializable):
    def __eq__(self, other):
        if isinstance(other, Message):
            return self.data == other.data
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

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

    def get_content(self, strict=True):
        # type: (bool) -> bytes
        """
        The HTTP message body decoded with the content-encoding header (e.g. gzip)

        Raises:
            ValueError, when the content-encoding is invalid and strict is True.

        See also: :py:class:`raw_content`, :py:attr:`text`
        """
        if self.raw_content is None:
            return None
        ce = self.headers.get("content-encoding")
        if ce:
            try:
                return encoding.decode(self.raw_content, ce)
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

    def _guess_encoding(self):
        # type: () -> str
        enc = self._get_content_type_charset()
        if enc:
            return enc

        if "json" in self.headers.get("content-type", ""):
            return "utf8"
        else:
            # We may also want to check for HTML meta tags here at some point.
            return "latin-1"

    def get_text(self, strict=True):
        # type: (bool) -> six.text_type
        """
        The HTTP message body decoded with both content-encoding header (e.g. gzip)
        and content-type header charset.

        Raises:
            ValueError, when either content-encoding or charset is invalid and strict is True.

        See also: :py:attr:`content`, :py:class:`raw_content`
        """
        if self.raw_content is None:
            return None
        enc = self._guess_encoding()

        content = self.get_content(strict)
        try:
            return encoding.decode(content, enc)
        except ValueError:
            if strict:
                raise
            return content.decode("utf8", "replace" if six.PY2 else "surrogateescape")

    def set_text(self, text):
        if text is None:
            self.content = None
            return
        enc = self._guess_encoding()

        try:
            self.content = encoding.encode(text, enc)
        except ValueError:
            # Fall back to UTF-8 and update the content-type header.
            ct = headers.parse_content_type(self.headers.get("content-type", "")) or ("text", "plain", {})
            ct[2]["charset"] = "utf-8"
            self.headers["content-type"] = headers.assemble_content_type(*ct)
            enc = "utf8"
            self.content = text.encode(enc, "replace" if six.PY2 else "surrogateescape")

    text = property(get_text, set_text)

    def decode(self, strict=True):
        """
        Decodes body based on the current Content-Encoding header, then
        removes the header. If there is no Content-Encoding header, no
        action is taken.

        Raises:
            ValueError, when the content-encoding is invalid and strict is True.
        """
        self.raw_content = self.get_content(strict)
        self.headers.pop("content-encoding", None)

    def encode(self, e):
        """
        Encodes body with the encoding e, where e is "gzip", "deflate", "identity", or "br".
        Any existing content-encodings are overwritten,
        the content is not decoded beforehand.

        Raises:
            ValueError, when the specified content-encoding is invalid.
        """
        self.headers["content-encoding"] = e
        self.content = self.raw_content
        if "content-encoding" not in self.headers:
            raise ValueError("Invalid content encoding {}".format(repr(e)))

    def replace(self, pattern, repl, flags=0, count=0):
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
                pattern, repl, self.content, flags=flags, count=count
            )
        replacements += self.headers.replace(pattern, repl, flags=flags, count=count)
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

    def __init__(self, message):  # pragma no cover
        warnings.warn("decoded() is deprecated, you can now directly use .content instead. "
                      ".raw_content has the encoded content.", DeprecationWarning)

    def __enter__(self):  # pragma no cover
        pass

    def __exit__(self, type, value, tb):  # pragma no cover
        pass
