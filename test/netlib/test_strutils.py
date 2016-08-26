import six

from netlib import strutils, tutils


def test_always_bytes():
    assert strutils.always_bytes(bytes(bytearray(range(256)))) == bytes(bytearray(range(256)))
    assert strutils.always_bytes("foo") == b"foo"
    with tutils.raises(ValueError):
        strutils.always_bytes(u"\u2605", "ascii")


def test_native():
    with tutils.raises(TypeError):
        strutils.native(42)
    if six.PY2:
        assert strutils.native(u"foo") == b"foo"
        assert strutils.native(b"foo") == b"foo"
    else:
        assert strutils.native(u"foo") == u"foo"
        assert strutils.native(b"foo") == u"foo"


def test_escape_control_characters():
    assert strutils.escape_control_characters(u"one") == u"one"
    assert strutils.escape_control_characters(u"\00ne") == u".ne"
    assert strutils.escape_control_characters(u"\nne") == u"\nne"
    assert strutils.escape_control_characters(u"\nne", False) == u".ne"
    assert strutils.escape_control_characters(u"\u2605") == u"\u2605"
    assert (
        strutils.escape_control_characters(bytes(bytearray(range(128))).decode()) ==
        u'.........\t\n..\r.................. !"#$%&\'()*+,-./0123456789:;<'
        u'=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~.'
    )
    assert (
        strutils.escape_control_characters(bytes(bytearray(range(128))).decode(), False) ==
        u'................................ !"#$%&\'()*+,-./0123456789:;<'
        u'=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~.'
    )

    if not six.PY2:
        with tutils.raises(ValueError):
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

    with tutils.raises(ValueError):
        strutils.bytes_to_escaped_str(u"such unicode")


def test_escaped_str_to_bytes():
    assert strutils.escaped_str_to_bytes("foo") == b"foo"
    assert strutils.escaped_str_to_bytes("\x08") == b"\b"
    assert strutils.escaped_str_to_bytes("&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes(u"\\x08") == b"\b"
    assert strutils.escaped_str_to_bytes(u"&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes(u"\u00fc") == b'\xc3\xbc'

    if six.PY2:
        with tutils.raises(ValueError):
            strutils.escaped_str_to_bytes(42)
    else:
        with tutils.raises(ValueError):
            strutils.escaped_str_to_bytes(b"very byte")


def test_is_mostly_bin():
    assert not strutils.is_mostly_bin(b"foo\xFF")
    assert strutils.is_mostly_bin(b"foo" + b"\xFF" * 10)
    assert not strutils.is_mostly_bin("")


def test_is_xml():
    assert not strutils.is_xml(b"foo")
    assert strutils.is_xml(b"<foo")
    assert strutils.is_xml(b"  \n<foo")


def test_clean_hanging_newline():
    s = "foo\n"
    assert strutils.clean_hanging_newline(s) == "foo"
    assert strutils.clean_hanging_newline("foo") == "foo"


def test_hexdump():
    assert list(strutils.hexdump(b"one\0" * 10))
