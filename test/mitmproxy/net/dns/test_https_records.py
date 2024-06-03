from hypothesis import given, strategies as st
from ipaddress import IPv4Address
from ipaddress import IPv6Address
from mitmproxy.net.dns import https_record

import pytest
import re
import struct


class TestHTTPSRecords:
    def test_simple(self):
        assert https_record.ALPN == 1
        assert https_record._SVCPARAMKEYS.get(1) == "alpn"

    def test_httpsrecord(self):
        with pytest.raises(TypeError, match=re.escape("HTTPSRecord.__init__() missing 3 required positional arguments: 'priority', 'target_name', and 'params'")):
            https_record.HTTPSRecord()

    def test_unpack(self):
        params = https_record.SVCParams(mandatory=[1,2,3], alpn=['h2', 'h3'], no_default_alpn=True, port=8000, ipv4hint=[IPv4Address('192.168.1.1'), IPv4Address('192.168.1.2')], ech="dGVzdHN0cmluZw==", ipv6hint=[IPv6Address('0000:0000:0000:0000:0000:0000:0000:0000'), IPv6Address('1050:0:0:0:5:600:300c:326b')])
        record = https_record.HTTPSRecord(1, "example.com", params)
        assert https_record.unpack(https_record.pack(record)) == record

        with pytest.raises(struct.error, match=re.escape("unpack requires a buffer of 2 bytes")):
            https_record.unpack(b'')

        with pytest.raises(struct.error, match=re.escape("unpack encountered illegal characters at offset 25")):
            https_record.unpack(b'\x00\x01\x07example\x03com\x00\x00\x01\x00\x06\x02\x872\x02h3')

        with pytest.raises(struct.error, match=re.escape("unpack encountered illegal characters at offset 3")):
            https_record.unpack(b'\x00\x01\x07exampl\x87\x03com\x00\x00\x01\x00\x06\x02h2\x02h3')

        with pytest.raises(struct.error, match=re.escape("unpack requires a buffer of 25 bytes")):
            https_record.unpack(b'\x00\x01\x07example\x03com\x00\x00\x01\x00\x06\x02h2')

        with pytest.raises(struct.error, match=re.escape("unpack requires a buffer of 10 bytes")):
            https_record.unpack(b'\x00\x01\x07exa')

        with pytest.raises(struct.error, match=re.escape("unknown SVCParamKey 255 found in HTTPS record")):
            https_record.unpack(b'\x00\x01\x07example\x03com\x00\x00\xff\x00\x06\x02h2\x02h3')


    def test_pack(self):
        params = https_record.SVCParams(mandatory=[1,2,3], alpn=['h2', 'h3'], no_default_alpn=True, port=8000, ipv4hint=[IPv4Address('192.168.1.1'), IPv4Address('192.168.1.2')], ech="dGVzdHN0cmluZw==", ipv6hint=[IPv6Address('0000:0000:0000:0000:0000:0000:0000:0000'), IPv6Address('1050:0:0:0:5:600:300c:326b')])
        record = https_record.HTTPSRecord(1, "example.com", params)
        assert https_record.pack(record) == b'\x00\x01\x07example\x03com\x00\x00\x00\x00\x06\x00\x01\x00\x02\x00\x03\x00\x01\x00\x06\x02h2\x02h3\x00\x02\x00\x00\x00\x03\x00\x02\x1f@\x00\x04\x00\x08\xc0\xa8\x01\x01\xc0\xa8\x01\x02\x00\x05\x00\nteststring\x00\x06\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10P\x00\x00\x00\x00\x00\x00\x00\x05\x06\x000\x0c2k'

    @given(st.binary())
    def test_fuzz_unpack(self, data: bytes):
        try:
            https_record.unpack(data)
        except struct.error:
            pass
