from netlib import utils
import tutils


def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b[1] == "a"
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(KeyError, b.__getitem__, 5)


def test_hexdump():
    assert utils.hexdump("one\0"*10)


def test_cleanBin():
    assert utils.cleanBin("one") == "one"
    assert utils.cleanBin("\00ne") == ".ne"
    assert utils.cleanBin("\nne") == "\nne"
    assert utils.cleanBin("\nne", True) == ".ne"
