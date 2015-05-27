from netlib import utils
import tutils


def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, utils.BiDi, one=1, two=1)


def test_hexdump():
    assert utils.hexdump("one\0" * 10)


def test_cleanBin():
    assert utils.cleanBin("one") == "one"
    assert utils.cleanBin("\00ne") == ".ne"
    assert utils.cleanBin("\nne") == "\nne"
    assert utils.cleanBin("\nne", True) == ".ne"


def test_pretty_size():
    assert utils.pretty_size(100) == "100B"
    assert utils.pretty_size(1024) == "1kB"
    assert utils.pretty_size(1024 + (1024 / 2.0)) == "1.5kB"
    assert utils.pretty_size(1024 * 1024) == "1MB"
