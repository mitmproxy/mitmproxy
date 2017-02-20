# coding=utf-8

from mitmproxy.net import check


def test_is_valid_host():
    assert not check.is_valid_host(b"")
    assert not check.is_valid_host(b"xn--ke.ws")
    assert check.is_valid_host(b"one.two")
    assert not check.is_valid_host(b"one" * 255)
    assert check.is_valid_host(b"one.two.")
    # Allow underscore
    assert check.is_valid_host(b"one_two")
    assert check.is_valid_host(b"::1")
