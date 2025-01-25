import re
import struct

import pytest

from mitmproxy.net.dns import domain_names
from mitmproxy.net.dns import types


def test_unpack_from_with_compression():
    assert domain_names.unpack_from_with_compression(
        b"\xff\x03www\x07example\x03org\x00", 1, domain_names.cache()
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
        b"\xff\xff\xff\x07example\x03org\x00\xff\xff\xff\x03www\xc0\x03",
        19,
        domain_names.cache(),
    ) == ("www.example.org", 6)


def test_unpack():
    assert domain_names.unpack(b"\x03www\x07example\x03org\x00") == "www.example.org"
    with pytest.raises(
        struct.error, match=re.escape("unpack requires a buffer of 17 bytes")
    ):
        domain_names.unpack(b"\x03www\x07example\x03org\x00\xff")
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
        match=re.escape("unpack encountered an illegal characters at offset 1"),
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


def test_record_data_can_have_compression():
    assert domain_names.record_data_can_have_compression(types.NS)
    assert not domain_names.record_data_can_have_compression(types.HTTPS)


def test_decompress_from_record_data():
    buffer = (
        b"\x10}\x81\x80\x00\x01\x00\x01\x00\x00\x00\x01\x06google\x03com\x00\x00\x06\x00\x01\xc0\x0c\x00\x06\x00"
        + b"\x01\x00\x00\x00\x0c\x00&\x03ns1\xc0\x0c\tdns-admin\xc0\x0c&~gw\x00\x00\x03\x84\x00\x00\x03\x84\x00"
        + b"\x00\x07\x08\x00\x00\x00<\x00\x00)\x02\x00\x00\x00\x00\x00\x00\x00"
    )
    assert (
        domain_names.decompress_from_record_data(buffer, 40, 78, domain_names.cache())
        == b"\x03ns1\x06google\x03com\x00\tdns-admin\x06google\x03com\x00&~gw\x00\x00\x03\x84\x00\x00\x03\x84\x00"
        + b"\x00\x07\x08\x00\x00\x00<"
    )


def test_record_data_contains_fake_pointer():
    # \xd2\a2 and \xc2\x00 seem like domain name compression pointers but are actually part of some other data type
    buffer = (
        b"\xfc\xc7\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00\x06google\x03com\x00\x00\x06\x00\x01\xc0\x0c\x00\x06\x00"
        + b"\x01\x00\x00\x008\x00&\x03ns1\xc0\x0c\tdns-admin\xc0\x0c&\xd2\xa2\xc2\x00\x00\x03\x84\x00\x00\x03\x84\x00"
        + b"\x00\x07\x08\x00\x00\x00<"
    )
    assert (
        domain_names.decompress_from_record_data(buffer, 40, 78, domain_names.cache())
        == b"\x03ns1\x06google\x03com\x00\tdns-admin\x06google\x03com\x00&\xd2\xa2\xc2\x00\x00\x03\x84\x00\x00\x03"
        + b"\x84\x00\x00\x07\x08\x00\x00\x00<"
    )
