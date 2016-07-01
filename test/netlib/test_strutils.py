# coding=utf-8
import six

from netlib import strutils, tutils


def test_native():
    with tutils.raises(TypeError):
        strutils.native(42)
    if six.PY2:
        assert strutils.native(u"foo") == b"foo"
        assert strutils.native(b"foo") == b"foo"
    else:
        assert strutils.native(u"foo") == u"foo"
        assert strutils.native(b"foo") == u"foo"


def test_clean_bin():
    assert strutils.clean_bin(b"one") == b"one"
    assert strutils.clean_bin(b"\00ne") == b".ne"
    assert strutils.clean_bin(b"\nne") == b"\nne"
    assert strutils.clean_bin(b"\nne", False) == b".ne"
    assert strutils.clean_bin(u"\u2605".encode("utf8")) == b"..."

    assert strutils.clean_bin(u"one") == u"one"
    assert strutils.clean_bin(u"\00ne") == u".ne"
    assert strutils.clean_bin(u"\nne") == u"\nne"
    assert strutils.clean_bin(u"\nne", False) == u".ne"
    assert strutils.clean_bin(u"\u2605") == u"\u2605"


def test_bytes_to_escaped_str():
    assert strutils.bytes_to_escaped_str(b"foo") == "foo"
    assert strutils.bytes_to_escaped_str(b"\b") == r"\x08"
    assert strutils.bytes_to_escaped_str(br"&!?=\)") == r"&!?=\\)"
    assert strutils.bytes_to_escaped_str(b'\xc3\xbc') == r"\xc3\xbc"
    assert strutils.bytes_to_escaped_str(b"'") == r"\'"
    assert strutils.bytes_to_escaped_str(b'"') == r'"'

    with tutils.raises(ValueError):
        strutils.bytes_to_escaped_str(u"such unicode")


def test_escaped_str_to_bytes():
    assert strutils.escaped_str_to_bytes("foo") == b"foo"
    assert strutils.escaped_str_to_bytes("\x08") == b"\b"
    assert strutils.escaped_str_to_bytes("&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes("ü") == b'\xc3\xbc'
    assert strutils.escaped_str_to_bytes(u"\\x08") == b"\b"
    assert strutils.escaped_str_to_bytes(u"&!?=\\\\)") == br"&!?=\)"
    assert strutils.escaped_str_to_bytes(u"ü") == b'\xc3\xbc'

    if six.PY2:
        with tutils.raises(ValueError):
            strutils.escaped_str_to_bytes(42)
    else:
        with tutils.raises(ValueError):
            strutils.escaped_str_to_bytes(b"very byte")


def test_isBin():
    assert not strutils.isBin("testing\n\r")
    assert strutils.isBin("testing\x01")
    assert strutils.isBin("testing\x0e")
    assert strutils.isBin("testing\x7f")


def test_isXml():
    assert not strutils.isXML("foo")
    assert strutils.isXML("<foo")
    assert strutils.isXML("  \n<foo")


def test_clean_hanging_newline():
    s = "foo\n"
    assert strutils.clean_hanging_newline(s) == "foo"
    assert strutils.clean_hanging_newline("foo") == "foo"


def test_hexdump():
    assert list(strutils.hexdump(b"one\0" * 10))
