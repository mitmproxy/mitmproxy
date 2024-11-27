import re
import struct

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mitmproxy.net.dns import https_records


class TestHTTPSRecords:
    def test_simple(self):
        assert https_records.SVCParamKeys.ALPN.value == 1
        assert https_records.SVCParamKeys(1).name == "ALPN"

    def test_httpsrecord(self):
        with pytest.raises(
            TypeError,
            match=re.escape(
                "HTTPSRecord.__init__() missing 3 required positional arguments: 'priority', 'target_name', and 'params'"
            ),
        ):
            https_records.HTTPSRecord()

    def test_unpack(self):
        params = {
            0: b"\x00\x04\x00\x06",
            1: b"\x02h2\x02h3",
            2: b"",
            3: b"\x01\xbb",
            4: b"\xb9\xc7l\x99\xb9\xc7m\x99\xb9\xc7n\x99\xb9\xc7o\x99",
            5: b"testbytes",
            6: b"&\x06P\xc0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x03\x00\x00\x00\x00\x00\x00\x00\x00\x01S",
        }
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert https_records.unpack(https_records.pack(record)) == record

        with pytest.raises(
            struct.error, match=re.escape("unpack requires a buffer of 2 bytes")
        ):
            https_records.unpack(b"")

        with pytest.raises(
            struct.error,
            match=re.escape("unpack encountered an illegal characters at offset 3"),
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
            struct.error, match=re.escape("unpack requires a label buffer of 7 bytes")
        ):
            https_records.unpack(b"\x00\x01\x07exa")

    def test_pack(self):
        params = {
            0: b"\x00\x04\x00\x06",
            1: b"\x02h2\x02h3",
            2: b"",
            3: b"\x01\xbb",
            4: b"\xb9\xc7l\x99\xb9\xc7m\x99\xb9\xc7n\x99\xb9\xc7o\x99",
            5: b"testbytes",
            6: b"&\x06P\xc0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x03\x00\x00\x00\x00\x00\x00\x00\x00\x01S",
        }
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert (
            https_records.pack(record)
            == b"\x00\x01\x07example\x03com\x00\x00\x00\x00\x04\x00\x04\x00\x06\x00\x01\x00\x06\x02h2\x02h3\x00\x02\x00\x00\x00\x03\x00\x02\x01\xbb\x00\x04\x00\x10\xb9\xc7l\x99\xb9\xc7m\x99\xb9\xc7n\x99\xb9\xc7o\x99\x00\x05\x00\ttestbytes\x00\x06\x00@&\x06P\xc0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01S&\x06P\xc0\x80\x03\x00\x00\x00\x00\x00\x00\x00\x00\x01S"
        )

        record = https_records.HTTPSRecord(1, "", {})
        assert https_records.pack(record) == b"\x00\x01\x00"

    @given(st.binary())
    def test_fuzz_unpack(self, data: bytes):
        try:
            https_records.unpack(data)
        except struct.error:
            pass

    def test_str(self):
        params = {
            0: b"\x00",
            1: b"\x01",
            2: b"",
            3: b"\x02",
            4: b"\x03",
            5: b"\x04",
            6: b"\x05",
        }
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert (
            str(record)
            == "priority: 1 target_name: 'example.com' {'mandatory': b'\\x00', 'alpn': b'\\x01', 'no_default_alpn': b'', 'port': b'\\x02', 'ipv4hint': b'\\x03', 'ech': b'\\x04', 'ipv6hint': b'\\x05'}"
        )

        params = {111: b"\x00"}
        record = https_records.HTTPSRecord(1, "example.com", params)
        assert (
            str(record) == "priority: 1 target_name: 'example.com' {'key111': b'\\x00'}"
        )
