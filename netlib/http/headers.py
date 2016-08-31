from __future__ import absolute_import, print_function, division

import re

import collections
import six
from netlib import multidict
from netlib import strutils

# See also: http://lucumr.pocoo.org/2013/7/2/the-updated-guide-to-unicode/

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


class Headers(multidict.MultiDict):
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

        # Headers can also be created from a list of raw (header_name, header_value) byte tuples
        >>> h = Headers([
            (b"Host",b"example.com"),
            (b"Accept",b"text/html"),
            (b"accept",b"application/xml")
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

    def __init__(self, fields=(), **headers):
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
        super(Headers, self).__init__(fields)

        for key, value in self.fields:
            if not isinstance(key, bytes) or not isinstance(value, bytes):
                raise TypeError("Header fields must be bytes.")

        # content_type -> content-type
        headers = {
            _always_bytes(name).replace(b"_", b"-"): _always_bytes(value)
            for name, value in six.iteritems(headers)
        }
        self.update(headers)

    @staticmethod
    def _reduce_values(values):
        # Headers can be folded
        return ", ".join(values)

    @staticmethod
    def _kconv(key):
        # Headers are case-insensitive
        return key.lower()

    def __bytes__(self):
        if self.fields:
            return b"\r\n".join(b": ".join(field) for field in self.fields) + b"\r\n"
        else:
            return b""

    if six.PY2:  # pragma: no cover
        __str__ = __bytes__

    def __delitem__(self, key):
        key = _always_bytes(key)
        super(Headers, self).__delitem__(key)

    def __iter__(self):
        for x in super(Headers, self).__iter__():
            yield _native(x)

    def get_all(self, name):
        """
        Like :py:meth:`get`, but does not fold multiple headers into a single one.
        This is useful for Set-Cookie headers, which do not support folding.
        See also: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        name = _always_bytes(name)
        return [
            _native(x) for x in
            super(Headers, self).get_all(name)
        ]

    def set_all(self, name, values):
        """
        Explicitly set multiple headers for the given key.
        See: :py:meth:`get_all`
        """
        name = _always_bytes(name)
        values = [_always_bytes(x) for x in values]
        return super(Headers, self).set_all(name, values)

    def insert(self, index, key, value):
        key = _always_bytes(key)
        value = _always_bytes(value)
        super(Headers, self).insert(index, key, value)

    def items(self, multi=False):
        if multi:
            return (
                (_native(k), _native(v))
                for k, v in self.fields
            )
        else:
            return super(Headers, self).items()

    def replace(self, pattern, repl, flags=0, count=0):
        """
        Replaces a regular expression pattern with repl in each "name: value"
        header line.

        Returns:
            The number of replacements made.
        """
        if isinstance(pattern, six.text_type):
            pattern = strutils.escaped_str_to_bytes(pattern)
        if isinstance(repl, six.text_type):
            repl = strutils.escaped_str_to_bytes(repl)
        pattern = re.compile(pattern, flags)
        replacements = 0
        flag_count = count > 0
        fields = []
        for name, value in self.fields:
            line, n = pattern.subn(repl, name + b": " + value, count=count)
            try:
                name, value = line.split(b": ", 1)
            except ValueError:
                # We get a ValueError if the replacement removed the ": "
                # There's not much we can do about this, so we just keep the header as-is.
                pass
            else:
                replacements += n
                if flag_count:
                    count -= n
                    if count == 0:
                        break
            fields.append((name, value))
        self.fields = tuple(fields)
        return replacements


def parse_content_type(c):
    """
        A simple parser for content-type values. Returns a (type, subtype,
        parameters) tuple, where type and subtype are strings, and parameters
        is a dict. If the string could not be parsed, return None.

        E.g. the following string:

            text/html; charset=UTF-8

        Returns:

            ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = collections.OrderedDict()
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def assemble_content_type(type, subtype, parameters):
    if not parameters:
        return "{}/{}".format(type, subtype)
    params = "; ".join(
        "{}={}".format(k, v)
        for k, v in parameters.items()
    )
    return "{}/{}; {}".format(
        type, subtype, params
    )
