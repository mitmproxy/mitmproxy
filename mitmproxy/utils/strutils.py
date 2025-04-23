import codecs
import io
import re
from collections.abc import Iterable
from typing import overload

# https://mypy.readthedocs.io/en/stable/more_types.html#function-overloading


@overload
def always_bytes(str_or_bytes: None, *encode_args) -> None: ...


@overload
def always_bytes(str_or_bytes: str | bytes, *encode_args) -> bytes: ...


def always_bytes(str_or_bytes: None | str | bytes, *encode_args) -> None | bytes:
    if str_or_bytes is None or isinstance(str_or_bytes, bytes):
        return str_or_bytes
    elif isinstance(str_or_bytes, str):
        return str_or_bytes.encode(*encode_args)
    else:
        raise TypeError(
            f"Expected str or bytes, but got {type(str_or_bytes).__name__}."
        )


@overload
def always_str(str_or_bytes: None, *encode_args) -> None: ...


@overload
def always_str(str_or_bytes: str | bytes, *encode_args) -> str: ...


def always_str(str_or_bytes: None | str | bytes, *decode_args) -> None | str:
    """
    Returns,
        str_or_bytes unmodified, if
    """
    if str_or_bytes is None or isinstance(str_or_bytes, str):
        return str_or_bytes
    elif isinstance(str_or_bytes, bytes):
        return str_or_bytes.decode(*decode_args)
    else:
        raise TypeError(
            f"Expected str or bytes, but got {type(str_or_bytes).__name__}."
        )


# Translate control characters to "safe" characters. This implementation
# initially replaced them with the matching control pictures
# (http://unicode.org/charts/PDF/U2400.pdf), but that turned out to render badly
# with monospace fonts. We are back to "." therefore.
_control_char_trans = {
    x: ord(".")
    for x in range(32)  # x + 0x2400 for unicode control group pictures
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
        raise ValueError(f"text type must be unicode but is {type(text).__name__}")

    trans = _control_char_trans_newline if keep_spacing else _control_char_trans
    return text.translate(trans)


def bytes_to_escaped_str(
    data: bytes, keep_spacing: bool = False, escape_single_quotes: bool = False
) -> str:
    """
    Take bytes and return a safe string that can be displayed to the user.

    Single quotes are always escaped, double quotes are never escaped:
        "'" + bytes_to_escaped_str(...) + "'"
    gives a valid Python string.

    Args:
        keep_spacing: If True, tabs and newlines will not be escaped.
    """

    if not isinstance(data, bytes):
        raise ValueError(f"data must be bytes, but is {data.__class__.__name__}")
    # We always insert a double-quote here so that we get a single-quoted string back
    # https://stackoverflow.com/questions/29019340/why-does-python-use-different-quotes-for-representing-strings-depending-on-their
    ret = repr(b'"' + data).lstrip("b")[2:-1]
    if not escape_single_quotes:
        ret = re.sub(r"(?<!\\)(\\\\)*\\'", lambda m: (m.group(1) or "") + "'", ret)
    if keep_spacing:
        ret = re.sub(
            r"(?<!\\)(\\\\)*\\([nrt])",
            lambda m: (m.group(1) or "") + dict(n="\n", r="\r", t="\t")[m.group(2)],
            ret,
        )
    return ret


def escaped_str_to_bytes(data: str) -> bytes:
    """
    Take an escaped string and return the unescaped bytes equivalent.

    Raises:
        ValueError, if the escape sequence is invalid.
    """
    if not isinstance(data, str):
        raise ValueError(f"data must be str, but is {data.__class__.__name__}")

    # This one is difficult - we use an undocumented Python API here
    # as per http://stackoverflow.com/a/23151714/934719
    return codecs.escape_decode(data)[0]  # type: ignore


def is_mostly_bin(s: bytes) -> bool:
    if not s or len(s) == 0:
        return False

    return sum(i < 9 or 13 < i < 32 or 126 < i for i in s[:100]) / len(s[:100]) > 0.3


def is_xml(s: bytes) -> bool:
    for char in s:
        if char in (9, 10, 32):  # is space?
            continue
        return char == 60  # is a "<"?
    return False


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
        offset = f"{i:0=10x}"
        part = s[i : i + 16]
        x = " ".join(f"{i:0=2x}" for i in part)
        x = x.ljust(47)  # 16*2 + 15
        part_repr = always_str(
            escape_control_characters(
                part.decode("ascii", "replace").replace("\ufffd", "."), False
            )
        )
        yield (offset, x, part_repr)


def _move_to_private_code_plane(matchobj):
    return chr(ord(matchobj.group(0)) + 0xE000)


def _restore_from_private_code_plane(matchobj):
    return chr(ord(matchobj.group(0)) - 0xE000)


NO_ESCAPE = r"(?<!\\)(?:\\\\)*"
MULTILINE_CONTENT = r"[\s\S]*?"
SINGLELINE_CONTENT = r".*?"
MULTILINE_CONTENT_LINE_CONTINUATION = r"(?:.|(?<=\\)\n)*?"


def split_special_areas(
    data: str,
    area_delimiter: Iterable[str],
):
    """
    Split a string of code into a [code, special area, code, special area, ..., code] list.

    For example,

    >>> split_special_areas(
    >>>     "test /* don't modify me */ foo",
    >>>     [r"/\\*[\\s\\S]*?\\*/"])  # (regex matching comments)
    ["test ", "/* don't modify me */", " foo"]

    "".join(split_special_areas(x, ...)) == x always holds true.
    """
    return re.split("({})".format("|".join(area_delimiter)), data, flags=re.MULTILINE)


def escape_special_areas(
    data: str,
    area_delimiter: Iterable[str],
    control_characters,
):
    """
    Escape all control characters present in special areas with UTF8 symbols
    in the private use plane (U+E000 t+ ord(char)).
    This is useful so that one can then use regex replacements on the resulting string without
    interfering with special areas.

    control_characters must be 0 < ord(x) < 256.

    Example:

    >>> print(x)
    if (true) { console.log('{}'); }
    >>> x = escape_special_areas(x, "{", ["'" + SINGLELINE_CONTENT + "'"])
    >>> print(x)
    if (true) { console.log('�}'); }
    >>> x = re.sub(r"\\s*{\\s*", " {\n    ", x)
    >>> x = unescape_special_areas(x)
    >>> print(x)
    if (true) {
        console.log('{}'); }
    """
    buf = io.StringIO()
    parts = split_special_areas(data, area_delimiter)
    rex = re.compile(rf"[{control_characters}]")
    for i, x in enumerate(parts):
        if i % 2:
            x = rex.sub(_move_to_private_code_plane, x)
        buf.write(x)
    return buf.getvalue()


def unescape_special_areas(data: str):
    """
    Invert escape_special_areas.

    x == unescape_special_areas(escape_special_areas(x)) always holds true.
    """
    return re.sub(r"[\ue000-\ue0ff]", _restore_from_private_code_plane, data)


def cut_after_n_lines(content: str, n: int) -> str:
    assert n > 0
    pos = content.find("\n")
    while pos >= 0 and n > 1:
        pos = content.find("\n", pos + 1)
        n -= 1
    if pos >= 0:
        content = content[: pos + 1]
    return content
