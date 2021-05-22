import pytest

from mitmproxy.utils import strutils


def test_always_bytes():
    assert strutils.always_bytes(bytes(range(256))) == bytes(range(256))
    assert strutils.always_bytes("foo") == b"foo"
    with pytest.raises(ValueError):
        strutils.always_bytes("\u2605", "ascii")
    with pytest.raises(TypeError):
        strutils.always_bytes(42, "ascii")


def test_always_str():
    with pytest.raises(TypeError):
        strutils.always_str(42)
    assert strutils.always_str("foo") == "foo"
    assert strutils.always_str(b"foo") == "foo"
    assert strutils.always_str(None) is None


def test_escape_control_characters():
    assert strutils.escape_control_characters("one") == "one"
    assert strutils.escape_control_characters("\00ne") == ".ne"
    assert strutils.escape_control_characters("\nne") == "\nne"
    assert strutils.escape_control_characters("\nne", False) == ".ne"
    assert strutils.escape_control_characters("\u2605") == "\u2605"
    assert (
        strutils.escape_control_characters(bytes(bytearray(range(128))).decode()) ==
        '.........\t\n..\r.................. !"#$%&\'()*+,-./0123456789:;<'
        '=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~.'
    )
    assert (
        strutils.escape_control_characters(bytes(bytearray(range(128))).decode(), False) ==
        '................................ !"#$%&\'()*+,-./0123456789:;<'
        '=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~.'
    )

    with pytest.raises(ValueError):
        strutils.escape_control_characters(b"foo")


def test_bytes_to_escaped_str():
    assert strutils.bytes_to_escaped_str(b"foo") == "foo"
    assert strutils.bytes_to_escaped_str(b"\b") == r"\x08"
    assert strutils.bytes_to_escaped_str(br"&!?=\)") == r"&!?=\\)"
    assert strutils.bytes_to_escaped_str(b'\xc3\xbc') == r"\xc3\xbc"
    assert strutils.bytes_to_escaped_str(b"'") == r"'"
    assert strutils.bytes_to_escaped_str(b'"') == r'"'

    assert strutils.bytes_to_escaped_str(b"'", escape_single_quotes=True) == r"\'"
    assert strutils.bytes_to_escaped_str(b'"', escape_single_quotes=True) == r'"'

    assert strutils.bytes_to_escaped_str(b"\r\n\t") == "\\r\\n\\t"
    assert strutils.bytes_to_escaped_str(b"\r\n\t", True) == "\r\n\t"

    assert strutils.bytes_to_escaped_str(b"\n", True) == "\n"
    assert strutils.bytes_to_escaped_str(b"\\n", True) == "\\ \\ n".replace(" ", "")
    assert strutils.bytes_to_escaped_str(b"\\\n", True) == "\\ \\ \n".replace(" ", "")
    assert strutils.bytes_to_escaped_str(b"\\\\n", True) == "\\ \\ \\ \\ n".replace(" ", "")

    with pytest.raises(ValueError):
        strutils.bytes_to_escaped_str("such unicode")


def test_escaped_str_to_bytes():
    assert strutils.escaped_str_to_bytes("foo") == b"foo"
    assert strutils.escaped_str_to_bytes("\x08") == b"\b"
    assert strutils.escaped_str_to_bytes("&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes("\\x08") == b"\b"
    assert strutils.escaped_str_to_bytes("&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes("\u00fc") == b'\xc3\xbc'

    with pytest.raises(ValueError):
        strutils.escaped_str_to_bytes(b"very byte")


def test_is_mostly_bin():
    assert not strutils.is_mostly_bin(b"foo\xFF")
    assert strutils.is_mostly_bin(b"foo" + b"\xFF" * 10)
    assert not strutils.is_mostly_bin("")


def test_is_xml():
    assert not strutils.is_xml(b"")
    assert not strutils.is_xml(b"foo")
    assert strutils.is_xml(b"<foo")
    assert strutils.is_xml(b"  \n<foo")


def test_clean_hanging_newline():
    s = "foo\n"
    assert strutils.clean_hanging_newline(s) == "foo"
    assert strutils.clean_hanging_newline("foo") == "foo"


def test_hexdump():
    assert list(strutils.hexdump(b"one\0" * 10))


ESCAPE_QUOTES = [
    "'" + strutils.SINGLELINE_CONTENT + strutils.NO_ESCAPE + "'",
    '"' + strutils.SINGLELINE_CONTENT + strutils.NO_ESCAPE + '"'
]


def test_split_special_areas():
    assert strutils.split_special_areas("foo", ESCAPE_QUOTES) == ["foo"]
    assert strutils.split_special_areas("foo 'bar' baz", ESCAPE_QUOTES) == ["foo ", "'bar'", " baz"]
    assert strutils.split_special_areas(
        """foo 'b\\'a"r' baz""",
        ESCAPE_QUOTES
    ) == ["foo ", "'b\\'a\"r'", " baz"]
    assert strutils.split_special_areas(
        "foo\n/*bar\nbaz*/\nqux",
        [r'/\*[\s\S]+?\*/']
    ) == ["foo\n", "/*bar\nbaz*/", "\nqux"]
    assert strutils.split_special_areas(
        "foo\n//bar\nbaz",
        [r'//.+$']
    ) == ["foo\n", "//bar", "\nbaz"]


def test_escape_special_areas():
    assert strutils.escape_special_areas('foo "bar" baz', ESCAPE_QUOTES, "*") == 'foo "bar" baz'
    esc = strutils.escape_special_areas('foo "b*r" b*z', ESCAPE_QUOTES, "*")
    assert esc == 'foo "b\ue02ar" b*z'
    assert strutils.unescape_special_areas(esc) == 'foo "b*r" b*z'
