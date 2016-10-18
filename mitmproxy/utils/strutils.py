import re
import codecs


def always_bytes(unicode_or_bytes, *encode_args):
    if isinstance(unicode_or_bytes, str):
        return unicode_or_bytes.encode(*encode_args)
    elif isinstance(unicode_or_bytes, bytes) or unicode_or_bytes is None:
        return unicode_or_bytes
    else:
        raise TypeError("Expected str or bytes, but got {}.".format(type(unicode_or_bytes).__name__))


def native(s, *encoding_opts):
    """
    Convert :py:class:`bytes` or :py:class:`unicode` to the native
    :py:class:`str` type, using latin1 encoding if conversion is necessary.

    https://www.python.org/dev/peps/pep-3333/#a-note-on-string-types
    """
    if not isinstance(s, (bytes, str)):
        raise TypeError("%r is neither bytes nor unicode" % s)
    if isinstance(s, bytes):
        return s.decode(*encoding_opts)
    return s


# Translate control characters to "safe" characters. This implementation initially
# replaced them with the matching control pictures (http://unicode.org/charts/PDF/U2400.pdf),
# but that turned out to render badly with monospace fonts. We are back to "." therefore.
_control_char_trans = {
    x: ord(".")  # x + 0x2400 for unicode control group pictures
    for x in range(32)
}
_control_char_trans[127] = ord(".")  # 0x2421
_control_char_trans_newline = _control_char_trans.copy()
for x in ("\r", "\n", "\t"):
    del _control_char_trans_newline[ord(x)]


_control_char_trans = str.maketrans(_control_char_trans)
_control_char_trans_newline = str.maketrans(_control_char_trans_newline)


def escape_control_characters(text: str, keep_spacing=True) -> str:
    """
    Replace all unicode C1 control characters from the given text with a single "."

    Args:
        keep_spacing: If True, tabs and newlines will not be replaced.
    """
    if not isinstance(text, str):
        raise ValueError("text type must be unicode but is {}".format(type(text).__name__))

    trans = _control_char_trans_newline if keep_spacing else _control_char_trans
    return text.translate(trans)


def bytes_to_escaped_str(data, keep_spacing=False, escape_single_quotes=False):
    """
    Take bytes and return a safe string that can be displayed to the user.

    Single quotes are always escaped, double quotes are never escaped:
        "'" + bytes_to_escaped_str(...) + "'"
    gives a valid Python string.

    Args:
        keep_spacing: If True, tabs and newlines will not be escaped.
    """

    if not isinstance(data, bytes):
        raise ValueError("data must be bytes, but is {}".format(data.__class__.__name__))
    # We always insert a double-quote here so that we get a single-quoted string back
    # https://stackoverflow.com/questions/29019340/why-does-python-use-different-quotes-for-representing-strings-depending-on-their
    ret = repr(b'"' + data).lstrip("b")[2:-1]
    if not escape_single_quotes:
        ret = re.sub(r"(?<!\\)(\\\\)*\\'", lambda m: (m.group(1) or "") + "'", ret)
    if keep_spacing:
        ret = re.sub(
            r"(?<!\\)(\\\\)*\\([nrt])",
            lambda m: (m.group(1) or "") + dict(n="\n", r="\r", t="\t")[m.group(2)],
            ret
        )
    return ret


def escaped_str_to_bytes(data):
    """
    Take an escaped string and return the unescaped bytes equivalent.

    Raises:
        ValueError, if the escape sequence is invalid.
    """
    if not isinstance(data, str):
        raise ValueError("data must be str, but is {}".format(data.__class__.__name__))

    # This one is difficult - we use an undocumented Python API here
    # as per http://stackoverflow.com/a/23151714/934719
    return codecs.escape_decode(data)[0]


def is_mostly_bin(s: bytes) -> bool:
    if not s or len(s) == 0:
        return False

    return sum(
        i < 9 or 13 < i < 32 or 126 < i
        for i in s[:100]
    ) / len(s[:100]) > 0.3


def is_xml(s: bytes) -> bool:
    return s.strip().startswith(b"<")


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
        offset = "{:0=10x}".format(i)
        part = s[i:i + 16]
        x = " ".join("{:0=2x}".format(i) for i in part)
        x = x.ljust(47)  # 16*2 + 15
        part_repr = native(escape_control_characters(
            part.decode("ascii", "replace").replace(u"\ufffd", u"."),
            False
        ))
        yield (offset, x, part_repr)
