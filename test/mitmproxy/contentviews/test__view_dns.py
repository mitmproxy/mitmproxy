import struct

import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_dns import dns
from mitmproxy.tcp import TCPMessage

DNS_HTTPS_RECORD_RESPONSE = bytes.fromhex(
    "00008180000100010000000107746c732d656368036465760000410001c00c004100010000003c00520001000005004b0049fe0d00"
    "452b00200020015881d41a3e2ef8f2208185dc479245d20624ddd0918a8056f2e26af47e2628000800010001000100034012707562"
    "6c69632e746c732d6563682e646576000000002904d0000000000000"
)
DNS_A_QUERY = bytes.fromhex("002a0100000100000000000003646e7306676f6f676c650000010001")
TCP_MESSAGE = struct.pack("!H", len(DNS_A_QUERY)) + DNS_A_QUERY


def test_simple():
    assert (
        dns.prettify(DNS_HTTPS_RECORD_RESPONSE, Metadata())
        == r"""id: 0
query: false
op_code: QUERY
authoritative_answer: false
truncation: false
recursion_desired: true
recursion_available: true
response_code: NOERROR
questions:
- name: tls-ech.dev
  type: HTTPS
  class: IN
answers:
- name: tls-ech.dev
  type: HTTPS
  class: IN
  ttl: 60
  data:
    target_name: ''
    priority: 1
    ech: \x00I\xfe\r\x00E+\x00 \x00 \x01X\x81\xd4\x1a>.\xf8\xf2 
      \x81\x85\xdcG\x92E\xd2\x06$\xdd\xd0\x91\x8a\x80V\xf2\xe2j\xf4~&(\x00\x08\x00\x01\x00\x01\x00\x01\x00\x03@\x12public.tls-ech.dev\x00\x00
authorities: []
additionals:
- name: ''
  type: OPT
  class: CLASS(1232)
  ttl: 0
  data: 0x
size: 82
"""
    )


def test_invalid():
    with pytest.raises(Exception):
        dns.prettify(b"foobar", Metadata())


def test_tcp():
    assert "type: A" in dns.prettify(
        TCP_MESSAGE, Metadata(tcp_message=TCPMessage(False, TCP_MESSAGE, 946681204.2))
    )


def test_roundtrip():
    meta = Metadata()
    assert dns.reencode(dns.prettify(DNS_A_QUERY, meta), meta) == DNS_A_QUERY


def test_render_priority():
    assert dns.render_priority(b"", Metadata(content_type="application/dns-message"))
    assert not dns.render_priority(b"", Metadata(content_type="text/plain"))
    assert not dns.render_priority(b"", Metadata())
