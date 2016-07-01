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


class Message(basetypes.Serializable):
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
    def content(self):
        """
        The raw (encoded) HTTP message body

        See also: :py:attr:`text`
        """
        return self.data.content

    @content.setter
    def content(self, content):
        self.data.content = content
        if isinstance(content, bytes):
            self.headers["content-length"] = str(len(content))

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

    @property
    def text(self):
        """
        The decoded HTTP message body.
        Decoded contents are not cached, so accessing this attribute repeatedly is relatively expensive.

        .. note::
            This is not implemented yet.

        See also: :py:attr:`content`, :py:class:`decoded`
        """
        # This attribute should be called text, because that's what requests does.
        raise NotImplementedError()

    @text.setter
    def text(self, text):
        raise NotImplementedError()

    def decode(self):
        """
            Decodes body based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.

            Returns:
                True, if decoding succeeded.
                False, otherwise.
        """
        ce = self.headers.get("content-encoding")
        data = encoding.decode(ce, self.content)
        if data is None:
            return False
        self.content = data
        self.headers.pop("content-encoding", None)
        return True

    def encode(self, e):
        """
            Encodes body with the encoding e, where e is "gzip", "deflate" or "identity".

            Returns:
                True, if decoding succeeded.
                False, otherwise.
        """
        data = encoding.encode(e, self.content)
        if data is None:
            return False
        self.content = data
        self.headers["content-encoding"] = e
        return True

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
            with decoded(self):
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
    A context manager that decodes a request or response, and then
    re-encodes it with the same encoding after execution of the block.

    Example:

    .. code-block:: python

        with decoded(request):
            request.content = request.content.replace("foo", "bar")
    """

    def __init__(self, message):
        self.message = message
        ce = message.headers.get("content-encoding")
        if ce in encoding.ENCODINGS:
            self.ce = ce
        else:
            self.ce = None

    def __enter__(self):
        if self.ce:
            self.message.decode()

    def __exit__(self, type, value, tb):
        if self.ce:
            self.message.encode(self.ce)
