# coding=utf-8

from netlib import utils, tutils


def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, utils.BiDi, one=1, two=1)


def test_hexdump():
    assert list(utils.hexdump(b"one\0" * 10))


def test_clean_bin():
    assert utils.clean_bin(b"one") == b"one"
    assert utils.clean_bin(b"\00ne") == b".ne"
    assert utils.clean_bin(b"\nne") == b"\nne"
    assert utils.clean_bin(b"\nne", False) == b".ne"
    assert utils.clean_bin(u"\u2605".encode("utf8")) == b"..."

    assert utils.clean_bin(u"one") == u"one"
    assert utils.clean_bin(u"\00ne") == u".ne"
    assert utils.clean_bin(u"\nne") == u"\nne"
    assert utils.clean_bin(u"\nne", False) == u".ne"
    assert utils.clean_bin(u"\u2605") == u"\u2605"


def test_safe_subn():
    assert utils.safe_subn("foo", u"bar", "\xc2foo")


def test_bytes_to_escaped_str():
    assert utils.bytes_to_escaped_str(b"foo") == "foo"
    assert utils.bytes_to_escaped_str(b"\b") == r"\x08"
    assert utils.bytes_to_escaped_str(br"&!?=\)") == r"&!?=\\)"
    assert utils.bytes_to_escaped_str(b'\xc3\xbc') == r"\xc3\xbc"
    assert utils.bytes_to_escaped_str(b"'") == r"\'"
    assert utils.bytes_to_escaped_str(b'"') == r'"'


def test_escaped_str_to_bytes():
    assert utils.escaped_str_to_bytes("foo") == b"foo"
    assert utils.escaped_str_to_bytes("\x08") == b"\b"
    assert utils.escaped_str_to_bytes("&!?=\\\\)") == br"&!?=\)"
    assert utils.escaped_str_to_bytes("ü") == b'\xc3\xbc'
    assert utils.escaped_str_to_bytes(u"\\x08") == b"\b"
    assert utils.escaped_str_to_bytes(u"&!?=\\\\)") == br"&!?=\)"
    assert utils.escaped_str_to_bytes(u"ü") == b'\xc3\xbc'
