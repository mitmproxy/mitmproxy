import time
from mitmproxy.utils import human
from mitmproxy.test import tutils


def test_format_timestamp():
    assert human.format_timestamp(time.time())


def test_format_timestamp_with_milli():
    assert human.format_timestamp_with_milli(time.time())


def test_parse_size():
    assert human.parse_size("0") == 0
    assert human.parse_size("0b") == 0
    assert human.parse_size("1") == 1
    assert human.parse_size("1k") == 1024
    assert human.parse_size("1m") == 1024**2
    assert human.parse_size("1g") == 1024**3
    tutils.raises(ValueError, human.parse_size, "1f")
    tutils.raises(ValueError, human.parse_size, "ak")


def test_pretty_size():
    assert human.pretty_size(0) == "0b"
    assert human.pretty_size(100) == "100b"
    assert human.pretty_size(1024) == "1k"
    assert human.pretty_size(1024 + (1024 / 2.0)) == "1.5k"
    assert human.pretty_size(1024 * 1024) == "1m"
    assert human.pretty_size(10 * 1024 * 1024) == "10m"


def test_pretty_duration():
    assert human.pretty_duration(0.00001) == "0ms"
    assert human.pretty_duration(0.0001) == "0ms"
    assert human.pretty_duration(0.001) == "1ms"
    assert human.pretty_duration(0.01) == "10ms"
    assert human.pretty_duration(0.1) == "100ms"
    assert human.pretty_duration(1) == "1.00s"
    assert human.pretty_duration(10) == "10.0s"
    assert human.pretty_duration(100) == "100s"
    assert human.pretty_duration(1000) == "1000s"
    assert human.pretty_duration(10000) == "10000s"
    assert human.pretty_duration(1.123) == "1.12s"
    assert human.pretty_duration(0.123) == "123ms"
