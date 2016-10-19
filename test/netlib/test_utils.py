# coding=utf-8

from netlib import utils


def test_is_valid_host():
    assert not utils.is_valid_host(b"")
    assert utils.is_valid_host(b"one.two")
    assert not utils.is_valid_host(b"one" * 255)
    assert utils.is_valid_host(b"one.two.")
