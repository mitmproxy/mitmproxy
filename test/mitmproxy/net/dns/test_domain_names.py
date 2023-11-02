import re
import struct

import pytest

from mitmproxy.net.dns import domain_names


def test_unpack_from_with_compression():
    assert domain_names.unpack_from_with_compression(
        b"\xFF\x03www\x07example\x03org\x00", 1, domain_names.cache()
    ) == (
        "www.example.org",
        17,
    )
    with pytest.raises(
        struct.error, match=re.escape("unpack encountered domain name loop")
    ):
        domain_names.unpack_from_with_compression(
            b"\x03www\xc0\x00", 0, domain_names.cache()
        )
    assert domain_names.unpack_from_with_compression(
        b"\xFF\xFF\xFF\x07example\x03org\x00\xFF\xFF\xFF\x03www\xc0\x03",
        19,
        domain_names.cache(),
    ) == ("www.example.org", 6)


def test_unpack():
    assert domain_names.unpack(b"\x03www\x07example\x03org\x00") == "www.example.org"
    with pytest.raises(
        struct.error, match=re.escape("unpack requires a buffer of 17 bytes")
    ):
        domain_names.unpack(b"\x03www\x07example\x03org\x00\xFF")
    with pytest.raises(
        struct.error,
        match=re.escape("unpack encountered a pointer which is not supported in RDATA"),
    ):
        domain_names.unpack(b"\x03www\x07example\x03org\xc0\x00")
    with pytest.raises(
        struct.error, match=re.escape("unpack requires a label buffer of 10 bytes")
    ):
        domain_names.unpack(b"\x0a")
    with pytest.raises(
        struct.error, match=re.escape("unpack encountered a label of length 64")
    ):
        domain_names.unpack(b"\x40" + (b"a" * 64) + b"\x00")
    with pytest.raises(
        struct.error,
        match=re.escape("unpack encountered a illegal characters at offset 1"),
    ):
        domain_names.unpack(b"\x03\xff\xff\xff\00")


def test_pack():
    assert domain_names.pack("") == b"\x00"
    with pytest.raises(
        ValueError, match=re.escape("domain name 'hello..world' contains empty labels")
    ):
        domain_names.pack("hello..world")
    label = "a" * 64
    name = f"www.{label}.com"
    with pytest.raises(
        ValueError,
        match="label too long",
    ):
        domain_names.pack(name)
    assert domain_names.pack("www.example.org") == b"\x03www\x07example\x03org\x00"
