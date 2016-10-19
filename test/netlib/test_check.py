# coding=utf-8

from netlib import check


def test_is_valid_host():
    assert not check.is_valid_host(b"")
    assert check.is_valid_host(b"one.two")
    assert not check.is_valid_host(b"one" * 255)
    assert check.is_valid_host(b"one.two.")
