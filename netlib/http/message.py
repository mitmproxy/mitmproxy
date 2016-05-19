from __future__ import absolute_import, print_function, division

import warnings

import six

from ..multidict import MultiDict
from .headers import Headers
from .. import encoding, utils

if six.PY2:  # pragma: no cover
    _native = lambda x: x
    _always_bytes = lambda x: x
else:
    # While the HTTP head _should_ be ASCII, it's not uncommon for certain headers to be utf-8 encoded.
    _native = lambda x: x.decode("utf-8", "surrogateescape")
    _always_bytes = lambda x: utils.always_bytes(x, "utf-8", "surrogateescape")


class MessageData(utils.Serializable):
    def __eq__(self, other):
        if isinstance(other, MessageData):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def set_state(self, state):
        for k, v in state.items():
            if k == "headers":
                v = Headers.from_state(v)
            setattr(self, k, v)

    def get_state(self):
        state = vars(self).copy()
        state["headers"] = state["headers"].get_state()
        return state

    @classmethod
    def from_state(cls, state):
        state["headers"] = Headers.from_state(state["headers"])
        return cls(**state)


class Message(utils.Serializable):
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
        state["headers"] = Headers.from_state(state["headers"])
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
        # TODO: Proper distinction between text and bytes.
        replacements = 0
        if self.content:
            with decoded(self):
                self.content, replacements = utils.safe_subn(
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


class MultiDictView(MultiDict):
    """
    Some parts in HTTP (Cookies, URL query strings, ...) require a specific data structure: A MultiDict.
    It behaves mostly like an ordered dict but it can have several values for the same key.

    The MultiDictView provides a MultiDict *view* on an :py:class:`Request` or :py:class:`Response`.
    That is, it represents a part of the request as a MultiDict, but doesn't contain state/data themselves.

    For example, ``request.cookies`` provides a view on the ``Cookie: ...`` header.
    Any change to ``request.cookies`` will also modify the ``Cookie`` header.
    Any change to the ``Cookie`` header will also modify ``request.cookies``.

    Example:

    .. code-block:: python

        # Cookies are represented as a MultiDict.
        >>> request.cookies
        MultiDictView[("name", "value"), ("a", "false"), ("a", "42")]

        # MultiDicts mostly behave like a normal dict.
        >>> request.cookies["name"]
        "value"

        # If there is more than one value, only the first value is returned.
        >>> request.cookies["a"]
        "false"

        # `.get_all(key)` returns a list of all values.
        >>> request.cookies.get_all("a")
        ["false", "42"]

        # Changes to the headers are immediately reflected in the cookies.
        >>> request.cookies
        MultiDictView[("name", "value"), ...]
        >>> del request.headers["Cookie"]
        >>> request.cookies
        MultiDictView[]  # empty now
    """

    def __init__(self, attr, message):
        if False:
            # We do not want to call the parent constructor here as that
            # would cause an unnecessary parse/unparse pass.
            # This is here to silence linters. Message
            super(MultiDictView, self).__init__(None)
        self._attr = attr
        self._message = message  # type: Message

    @staticmethod
    def _kconv(key):
        # All request-attributes are case-sensitive.
        return key

    @staticmethod
    def _reduce_values(values):
        # We just return the first element if
        # multiple elements exist with the same key.
        return values[0]

    @property
    def fields(self):
        return getattr(self._message, "_" + self._attr)

    @fields.setter
    def fields(self, value):
        setattr(self._message, self._attr, value)
