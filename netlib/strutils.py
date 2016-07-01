import unicodedata
import codecs

import six


def always_bytes(unicode_or_bytes, *encode_args):
    if isinstance(unicode_or_bytes, six.text_type):
        return unicode_or_bytes.encode(*encode_args)
    return unicode_or_bytes


def native(s, *encoding_opts):
    """
    Convert :py:class:`bytes` or :py:class:`unicode` to the native
    :py:class:`str` type, using latin1 encoding if conversion is necessary.

    https://www.python.org/dev/peps/pep-3333/#a-note-on-string-types
    """
    if not isinstance(s, (six.binary_type, six.text_type)):
        raise TypeError("%r is neither bytes nor unicode" % s)
    if six.PY3:
        if isinstance(s, six.binary_type):
            return s.decode(*encoding_opts)
    else:
        if isinstance(s, six.text_type):
            return s.encode(*encoding_opts)
    return s


def clean_bin(s, keep_spacing=True):
    """
        Cleans binary data to make it safe to display.

        Args:
            keep_spacing: If False, tabs and newlines will also be replaced.
    """
    if isinstance(s, six.text_type):
        if keep_spacing:
            keep = u" \n\r\t"
        else:
            keep = u" "
        return u"".join(
            ch if (unicodedata.category(ch)[0] not in "CZ" or ch in keep) else u"."
            for ch in s
        )
    else:
        if keep_spacing:
            keep = (9, 10, 13)  # \t, \n, \r,
        else:
            keep = ()
        return b"".join(
            six.int2byte(ch) if (31 < ch < 127 or ch in keep) else b"."
            for ch in six.iterbytes(s)
        )


def bytes_to_escaped_str(data):
    """
    Take bytes and return a safe string that can be displayed to the user.

    Single quotes are always escaped, double quotes are never escaped:
        "'" + bytes_to_escaped_str(...) + "'"
    gives a valid Python string.
    """
    # TODO: We may want to support multi-byte characters without escaping them.
    # One way to do would be calling .decode("utf8", "backslashreplace") first
    # and then escaping UTF8 control chars (see clean_bin).

    if not isinstance(data, bytes):
        raise ValueError("data must be bytes, but is {}".format(data.__class__.__name__))
    # We always insert a double-quote here so that we get a single-quoted string back
    # https://stackoverflow.com/questions/29019340/why-does-python-use-different-quotes-for-representing-strings-depending-on-their
    return repr(b'"' + data).lstrip("b")[2:-1]


def escaped_str_to_bytes(data):
    """
    Take an escaped string and return the unescaped bytes equivalent.
    """
    if not isinstance(data, six.string_types):
        if six.PY2:
            raise ValueError("data must be str or unicode, but is {}".format(data.__class__.__name__))
        raise ValueError("data must be str, but is {}".format(data.__class__.__name__))

    if six.PY2:
        if isinstance(data, unicode):
            data = data.encode("utf8")
        return data.decode("string-escape")

    # This one is difficult - we use an undocumented Python API here
    # as per http://stackoverflow.com/a/23151714/934719
    return codecs.escape_decode(data)[0]


def isBin(s):
    """
        Does this string have any non-ASCII characters?
    """
    for i in s:
        i = ord(i)
        if i < 9 or 13 < i < 32 or 126 < i:
            return True
    return False


def isMostlyBin(s):
    s = s[:100]
    return sum(isBin(ch) for ch in s) / len(s) > 0.3


def isXML(s):
    return s.strip().startswith("<")


def clean_hanging_newline(t):
    """
        Many editors will silently add a newline to the final line of a
        document (I'm looking at you, Vim). This function fixes this common
        problem at the risk of removing a hanging newline in the rare cases
        where the user actually intends it.
    """
    if t and t[-1] == "\n":
        return t[:-1]
    return t


def hexdump(s):
    """
        Returns:
            A generator of (offset, hex, str) tuples
    """
    for i in range(0, len(s), 16):
        offset = "{:0=10x}".format(i).encode()
        part = s[i:i + 16]
        x = b" ".join("{:0=2x}".format(i).encode() for i in six.iterbytes(part))
        x = x.ljust(47)  # 16*2 + 15
        yield (offset, x, clean_bin(part, False))
