# coding=utf-8

from netlib import utils, tutils


def test_is_valid_host():
    assert not utils.is_valid_host(b"")
    assert utils.is_valid_host(b"one.two")
    assert not utils.is_valid_host(b"one" * 255)
    assert utils.is_valid_host(b"one.two.")


def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, utils.BiDi, one=1, two=1)
