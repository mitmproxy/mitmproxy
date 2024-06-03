import re
import struct
from ipaddress import IPv4Address
from ipaddress import IPv6Address

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mitmproxy.net.dns import https_records


class TestHTTPSRecords:
    def test_simple(self):
        assert https_records.ALPN == 1
        assert https_records._SVCPARAMKEYS.get(1) == "alpn"

    def test_httpsrecord(self):
        with pytest.raises(
            TypeError,
            match=re.escape(
                "HTTPSRecord.__init__() missing 3 required positional arguments: 'priority', 'target_name', and 'params'"
            ),
        ):
            https_records.HTTPSRecord()

    def test_unpack(self):
        params = https_records.SVCParams(
            mandatory=[1, 2, 3],
            alpn=["h2", "h3"],
            no_default_alpn=True,
            port=8000,
            ipv4hint=[IPv4Address("192.168.1.1"), IPv4Address("192.168.1.2")],
            ech="dGVzdHN0cmluZw==",
            ipv6hint=[
                IPv6Address("0000:0000:0000:0000:0000:0000:0000:0000"),
                IPv6Address("1050:0:0:0:5:600:300c:326b"),
            ],
        )
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert https_records.unpack(https_records.pack(record)) == record

        with pytest.raises(
            struct.error, match=re.escape("unpack requires a buffer of 2 bytes")
        ):
            https_records.unpack(b"")

        with pytest.raises(
            struct.error,
            match=re.escape("unpack encountered illegal characters at offset 25"),
        ):
            https_records.unpack(
                b"\x00\x01\x07example\x03com\x00\x00\x01\x00\x06\x02\x872\x02h3"
            )

        with pytest.raises(
            struct.error,
            match=re.escape("unpack encountered illegal characters at offset 3"),
        ):
            https_records.unpack(
                b"\x00\x01\x07exampl\x87\x03com\x00\x00\x01\x00\x06\x02h2\x02h3"
            )

        with pytest.raises(
            struct.error, match=re.escape("unpack requires a buffer of 25 bytes")
        ):
            https_records.unpack(
                b"\x00\x01\x07example\x03com\x00\x00\x01\x00\x06\x02h2"
            )

        with pytest.raises(
            struct.error, match=re.escape("unpack requires a buffer of 10 bytes")
        ):
            https_records.unpack(b"\x00\x01\x07exa")

        with pytest.raises(
            struct.error,
            match=re.escape("unknown SVCParamKey 255 found in HTTPS record"),
        ):
            https_records.unpack(
                b"\x00\x01\x07example\x03com\x00\x00\xff\x00\x06\x02h2\x02h3"
            )

    def test_pack(self):
        params = https_records.SVCParams(
            mandatory=[1, 2, 3],
            alpn=["h2", "h3"],
            no_default_alpn=True,
            port=8000,
            ipv4hint=[IPv4Address("192.168.1.1"), IPv4Address("192.168.1.2")],
            ech="dGVzdHN0cmluZw==",
            ipv6hint=[
                IPv6Address("0000:0000:0000:0000:0000:0000:0000:0000"),
                IPv6Address("1050:0:0:0:5:600:300c:326b"),
            ],
        )
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert (
            https_records.pack(record)
            == b"\x00\x01\x07example\x03com\x00\x00\x00\x00\x06\x00\x01\x00\x02\x00\x03\x00\x01\x00\x06\x02h2\x02h3\x00\x02\x00\x00\x00\x03\x00\x02\x1f@\x00\x04\x00\x08\xc0\xa8\x01\x01\xc0\xa8\x01\x02\x00\x05\x00\nteststring\x00\x06\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10P\x00\x00\x00\x00\x00\x00\x00\x05\x06\x000\x0c2k"
        )

        record = https_records.HTTPSRecord(1, "", https_records.SVCParams())
        assert https_records.pack(record) == b"\x00\x01\x00"

    @given(st.binary())
    def test_fuzz_unpack(self, data: bytes):
        try:
            https_records.unpack(data)
        except struct.error:
            pass

    def test_str(self):
        params = https_records.SVCParams(
            mandatory=[1, 2, 3],
            alpn=["h2", "h3"],
            no_default_alpn=True,
            port=8000,
            ipv4hint=[IPv4Address("192.168.1.1")],
            ech="test",
            ipv6hint=[IPv6Address("1050:0000:0000:0000:0005:0600:300c:326b")],
        )
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert (
            str(record)
            == "priority=1 target_name=\"example.com\" mandatory=['alpn', 'no-default-alpn', 'port'] alpn=['h2', 'h3'] no-default-alpn=True port=8000 ipv4hint=['192.168.1.1'] ech=\"test\" ipv6hint=['1050::5:600:300c:326b']"
        )
