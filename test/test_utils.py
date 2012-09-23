from netlib import utils


def test_hexdump():
    assert utils.hexdump("one\0"*10)


def test_cleanBin():
    assert utils.cleanBin("one") == "one"
    assert utils.cleanBin("\00ne") == ".ne"
    assert utils.cleanBin("\nne") == "\nne"
    assert utils.cleanBin("\nne", True) == ".ne"

