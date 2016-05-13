"""

Unicode Handling
----------------
See also: http://lucumr.pocoo.org/2013/7/2/the-updated-guide-to-unicode/
"""
from __future__ import absolute_import, print_function, division

import re

try:
    from collections.abc import MutableMapping
except ImportError:  # pragma: no cover
    from collections import MutableMapping  # Workaround for Python < 3.3


import six

from netlib.utils import always_byte_args, always_bytes, Serializable

if six.PY2:  # pragma: no cover
    _native = lambda x: x
    _always_bytes = lambda x: x
    _always_byte_args = lambda x: x
else:
    # While headers _should_ be ASCII, it's not uncommon for certain headers to be utf-8 encoded.
    _native = lambda x: x.decode("utf-8", "surrogateescape")
    _always_bytes = lambda x: always_bytes(x, "utf-8", "surrogateescape")
    _always_byte_args = always_byte_args("utf-8", "surrogateescape")


class Headers(MutableMapping, Serializable):
    """
    Header class which allows both convenient access to individual headers as well as
    direct access to the underlying raw data. Provides a full dictionary interface.

    Example:

    .. code-block:: python

        # Create headers with keyword arguments
        >>> h = Headers(host="example.com", content_type="application/xml")

        # Headers mostly behave like a normal dict.
        >>> h["Host"]
        "example.com"

        # HTTP Headers are case insensitive
        >>> h["host"]
        "example.com"

        # Headers can also be creatd from a list of raw (header_name, header_value) byte tuples
        >>> h = Headers([
            [b"Host",b"example.com"],
            [b"Accept",b"text/html"],
            [b"accept",b"application/xml"]
        ])

        # Multiple headers are folded into a single header as per RFC7230
        >>> h["Accept"]
        "text/html, application/xml"

        # Setting a header removes all existing headers with the same name.
        >>> h["Accept"] = "application/text"
        >>> h["Accept"]
        "application/text"

        # bytes(h) returns a HTTP1 header block.
        >>> print(bytes(h))
        Host: example.com
        Accept: application/text

        # For full control, the raw header fields can be accessed
        >>> h.fields

    Caveats:
        For use with the "Set-Cookie" header, see :py:meth:`get_all`.
    """

    @_always_byte_args
    def __init__(self, fields=None, **headers):
        """
        Args:
            fields: (optional) list of ``(name, value)`` header byte tuples,
                e.g. ``[(b"Host", b"example.com")]``. All names and values must be bytes.
            **headers: Additional headers to set. Will overwrite existing values from `fields`.
                For convenience, underscores in header names will be transformed to dashes -
                this behaviour does not extend to other methods.
                If ``**headers`` contains multiple keys that have equal ``.lower()`` s,
                the behavior is undefined.
        """
        self.fields = fields or []

        for name, value in self.fields:
            if not isinstance(name, bytes) or not isinstance(value, bytes):
                raise ValueError("Headers passed as fields must be bytes.")

        # content_type -> content-type
        headers = {
            _always_bytes(name).replace(b"_", b"-"): value
            for name, value in six.iteritems(headers)
            }
        self.update(headers)

    def __bytes__(self):
        if self.fields:
            return b"\r\n".join(b": ".join(field) for field in self.fields) + b"\r\n"
        else:
            return b""

    if six.PY2:  # pragma: no cover
        __str__ = __bytes__

    @_always_byte_args
    def __getitem__(self, name):
        values = self.get_all(name)
        if not values:
            raise KeyError(name)
        return ", ".join(values)

    @_always_byte_args
    def __setitem__(self, name, value):
        idx = self._index(name)

        # To please the human eye, we insert at the same position the first existing header occured.
        if idx is not None:
            del self[name]
            self.fields.insert(idx, [name, value])
        else:
            self.fields.append([name, value])

    @_always_byte_args
    def __delitem__(self, name):
        if name not in self:
            raise KeyError(name)
        name = name.lower()
        self.fields = [
            field for field in self.fields
            if name != field[0].lower()
        ]

    def __iter__(self):
        seen = set()
        for name, _ in self.fields:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                yield _native(name)

    def __len__(self):
        return len(set(name.lower() for name, _ in self.fields))

    # __hash__ = object.__hash__

    def _index(self, name):
        name = name.lower()
        for i, field in enumerate(self.fields):
            if field[0].lower() == name:
                return i
        return None

    def __eq__(self, other):
        if isinstance(other, Headers):
            return self.fields == other.fields
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @_always_byte_args
    def get_all(self, name):
        """
        Like :py:meth:`get`, but does not fold multiple headers into a single one.
        This is useful for Set-Cookie headers, which do not support folding.

        See also: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        name_lower = name.lower()
        values = [_native(value) for n, value in self.fields if n.lower() == name_lower]
        return values

    @_always_byte_args
    def set_all(self, name, values):
        """
        Explicitly set multiple headers for the given key.
        See: :py:meth:`get_all`
        """
        values = map(_always_bytes, values)  # _always_byte_args does not fix lists
        if name in self:
            del self[name]
        self.fields.extend(
            [name, value] for value in values
        )

    def get_state(self):
        return tuple(tuple(field) for field in self.fields)

    def set_state(self, state):
        self.fields = [list(field) for field in state]

    @classmethod
    def from_state(cls, state):
        return cls([list(field) for field in state])

    @_always_byte_args
    def replace(self, pattern, repl, flags=0):
        """
        Replaces a regular expression pattern with repl in each "name: value"
        header line.

        Returns:
            The number of replacements made.
        """
        pattern = re.compile(pattern, flags)
        replacements = 0

        fields = []
        for name, value in self.fields:
            line, n = pattern.subn(repl, name + b": " + value)
            try:
                name, value = line.split(b": ", 1)
            except ValueError:
                # We get a ValueError if the replacement removed the ": "
                # There's not much we can do about this, so we just keep the header as-is.
                pass
            else:
                replacements += n
            fields.append([name, value])
        self.fields = fields
        return replacements
