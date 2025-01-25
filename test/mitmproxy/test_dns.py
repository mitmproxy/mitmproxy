import ipaddress
import struct

import pytest

from mitmproxy import dns
from mitmproxy import flowfilter
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestResourceRecord:
    def test_str(self):
        assert (
            str(dns.ResourceRecord.A("test", ipaddress.IPv4Address("1.2.3.4")))
            == "1.2.3.4"
        )
        assert (
            str(dns.ResourceRecord.AAAA("test", ipaddress.IPv6Address("::1"))) == "::1"
        )
        assert (
            str(dns.ResourceRecord.CNAME("test", "some.other.host"))
            == "some.other.host"
        )
        assert (
            str(dns.ResourceRecord.PTR("test", "some.other.host")) == "some.other.host"
        )
        assert (
            str(dns.ResourceRecord.TXT("test", "unicode text 😀")) == "unicode text 😀"
        )
        params = {
            0: b"\x00",
            1: b"\x01",
            2: b"",
            3: b"\x02",
            4: b"\x03",
            5: b"\x04",
            6: b"\x05",
        }
        record = dns.https_records.HTTPSRecord(1, "example.com", params)
        assert (
            str(dns.ResourceRecord.HTTPS("example.com", record))
            == "priority: 1 target_name: 'example.com' {'mandatory': b'\\x00', 'alpn': b'\\x01', 'no_default_alpn': b'', 'port': b'\\x02', 'ipv4hint': b'\\x03', 'ech': b'\\x04', 'ipv6hint': b'\\x05'}"
        )
        assert (
            str(
                dns.ResourceRecord(
                    "test",
                    dns.types.A,
                    dns.classes.IN,
                    dns.ResourceRecord.DEFAULT_TTL,
                    b"",
                )
            )
            == "0x (invalid A data)"
        )
        assert (
            str(
                dns.ResourceRecord(
                    "test",
                    dns.types.SOA,
                    dns.classes.IN,
                    dns.ResourceRecord.DEFAULT_TTL,
                    b"\x00\x01\x02\x03",
                )
            )
            == "0x00010203"
        )

    def test_setter(self):
        rr = dns.ResourceRecord(
            "test", dns.types.ANY, dns.classes.IN, dns.ResourceRecord.DEFAULT_TTL, b""
        )
        rr.ipv4_address = ipaddress.IPv4Address("8.8.4.4")
        assert rr.ipv4_address == ipaddress.IPv4Address("8.8.4.4")
        rr.ipv6_address = ipaddress.IPv6Address("2001:4860:4860::8844")
        assert rr.ipv6_address == ipaddress.IPv6Address("2001:4860:4860::8844")
        rr.domain_name = "www.example.org"
        assert rr.domain_name == "www.example.org"
        rr.text = "sample text"
        assert rr.text == "sample text"

    def test_https_record_ech(self):
        rr = dns.ResourceRecord(
            "test", dns.types.ANY, dns.classes.IN, dns.ResourceRecord.DEFAULT_TTL, b""
        )
        params = {3: b"\x01\xbb"}
        record = dns.https_records.HTTPSRecord(1, "example.org", params)
        rr.data = dns.https_records.pack(record)
        assert rr.https_ech is None
        rr.https_ech = "dGVzdHN0cmluZwo="
        assert rr.https_ech == "dGVzdHN0cmluZwo="
        rr.https_ech = None
        assert rr.https_ech is None

    def test_https_record_alpn(self):
        rr = dns.ResourceRecord(
            "test", dns.types.ANY, dns.classes.IN, dns.ResourceRecord.DEFAULT_TTL, b""
        )
        record = dns.https_records.HTTPSRecord(1, "example.org", {})
        rr.data = dns.https_records.pack(record)

        assert rr.https_alpn is None
        assert rr.data == b"\x00\x01\x07example\x03org\x00"

        rr.https_alpn = [b"h2", b"h3"]
        assert rr.https_alpn == (b"h2", b"h3")
        assert rr.data == b"\x00\x01\x07example\x03org\x00\x00\x01\x00\x06\x02h2\x02h3"

        rr.https_alpn = None
        assert rr.https_alpn is None
        assert rr.data == b"\x00\x01\x07example\x03org\x00"


class TestMessage:
    def test_json(self):
        resp = tutils.tdnsresp()
        json = resp.to_json()
        assert json["id"] == resp.id
        assert len(json["questions"]) == len(resp.questions)
        assert json["questions"][0]["name"] == resp.questions[0].name
        assert len(json["answers"]) == len(resp.answers)
        assert json["answers"][0]["data"] == str(resp.answers[0])

    def test_responses(self):
        req = tutils.tdnsreq()
        resp = tutils.tdnsresp()
        resp2 = req.succeed(
            [
                dns.ResourceRecord.A(
                    "dns.google", ipaddress.IPv4Address("8.8.8.8"), ttl=32
                ),
                dns.ResourceRecord.A(
                    "dns.google", ipaddress.IPv4Address("8.8.4.4"), ttl=32
                ),
            ]
        )
        resp2.timestamp = resp.timestamp
        assert resp == resp2
        assert resp2.size == 8
        with pytest.raises(ValueError):
            req.fail(dns.response_codes.NOERROR)
        assert (
            req.fail(dns.response_codes.FORMERR).response_code
            == dns.response_codes.FORMERR
        )

    def test_range(self):
        def test(what: str, min: int, max: int):
            req = tutils.tdnsreq()
            setattr(req, what, min)
            assert getattr(dns.Message.unpack(req.packed), what) == min
            setattr(req, what, min - 1)
            with pytest.raises(ValueError):
                req.packed
            setattr(req, what, max)
            assert getattr(dns.Message.unpack(req.packed), what) == max
            setattr(req, what, max + 1)
            with pytest.raises(ValueError):
                req.packed

        test("id", 0, 2**16 - 1)
        test("reserved", 0, 7)
        test("op_code", 0, 0b1111)
        test("response_code", 0, 0b1111)

    def test_packing(self):
        def assert_eq(m: dns.Message, b: bytes) -> None:
            m_b = dns.Message.unpack(b)
            m_b.timestamp = m.timestamp
            assert m_b == m
            assert m_b.packed == m.packed

        assert_eq(
            tutils.tdnsreq(),
            b"\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01",
        )
        with pytest.raises(struct.error):
            dns.Message.unpack(
                b"\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01\x00"
            )
        assert_eq(
            tutils.tdnsresp(),
            (
                b"\x00\x2a\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01"
                b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x08\x08\xc0\x0c\x00\x01\x00\x01"
                b"\x00\x00\x00 \x00\x04\x08\x08\x04\x04"
            ),
        )
        with pytest.raises(struct.error):  # question error
            dns.Message.unpack(
                b"\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06goo"
            )
        with pytest.raises(struct.error):  # rr length error
            dns.Message.unpack(
                b"\x00\x2a\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01"
                + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x08\x08\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x04"
            )
        txt = dns.Message.unpack(
            b"V\x1a\x81\x80\x00\x01\x00\x01\x00\x01\x00\x01\x05alive\x06github\x03com\x00\x00"
            + b"\x10\x00\x01\xc0\x0c\x00\x05\x00\x01\x00\x00\x0b\xc6\x00\x07\x04live\xc0\x12\xc0\x12\x00\x06\x00\x01"
            + b"\x00\x00\x03\x84\x00H\x07ns-1707\tawsdns-21\x02co\x02uk\x00\x11awsdns-hostmaster\x06amazon\xc0\x19\x00"
            + b"\x00\x00\x01\x00\x00\x1c \x00\x00\x03\x84\x00\x12u\x00\x00\x01Q\x80\x00\x00)\x02\x00\x00\x00\x00\x00\x00\x00"
        )
        assert txt.answers[0].domain_name == "live.github.com"
        invalid_rr_domain_name = dns.Message.unpack(
            b"V\x1a\x81\x80\x00\x01\x00\x01\x00\x01\x00\x01\x05alive\x06github\x03com\x00\x00"
            + b"\x10\x00\x01\xc0\x0c\x00\x05\x00\x01\x00\x00\x0b\xc6\x00\x07\x99live\xc0\x12\xc0\x12\x00\x06\x00\x01"
            + b"\x00\x00\x03\x84\x00H\x07ns-1707\tawsdns-21\x02co\x02uk\x00\x11awsdns-hostmaster\x06amazon\xc0\x19\x00"
            + b"\x00\x00\x01\x00\x00\x1c \x00\x00\x03\x84\x00\x12u\x00\x00\x01Q\x80\x00\x00)\x02\x00\x00\x00\x00\x00\x00\x00"
        )
        assert (
            invalid_rr_domain_name.answers[0].data == b"\x99live\x06github\x03com\x00"
        )
        valid_compressed_rr_data = dns.Message.unpack(
            b"\x10}\x81\x80\x00\x01\x00\x01\x00\x00\x00\x01\x06google\x03com\x00\x00\x06\x00\x01\xc0\x0c\x00\x06\x00"
            + b"\x01\x00\x00\x00\x0c\x00&\x03ns1\xc0\x0c\tdns-admin\xc0\x0c&~gw\x00\x00\x03\x84\x00\x00\x03\x84\x00"
            + b"\x00\x07\x08\x00\x00\x00<\x00\x00)\x02\x00\x00\x00\x00\x00\x00\x00"
        )
        assert (
            valid_compressed_rr_data.answers[0].data
            == b"\x03ns1\x06google\x03com\x00\tdns-admin\x06google\x03com\x00&~gw\x00\x00\x03\x84\x00\x00\x03\x84\x00"
            + b"\x00\x07\x08\x00\x00\x00<"
        )
        A_record_data_contains_pointer_label = dns.Message.unpack(
            b"\x98A\x81\x80\x00\x01\x00\x01\x00\x00\x00\x01\x06google\x03com\x00\x00\x01\x00\x01\xc0\x0c\x00\x01\x00"
            + b"\x01\x00\x00\x00/\x00\x04\xd8:\xc4\xae\x00\x00)\x02\x00\x00\x00\x00\x00\x00\x00"
        )
        assert A_record_data_contains_pointer_label.answers[0].data == b"\xd8:\xc4\xae"
        req = tutils.tdnsreq()
        for flag in (
            "authoritative_answer",
            "truncation",
            "recursion_desired",
            "recursion_available",
        ):
            setattr(req, flag, True)
            assert getattr(dns.Message.unpack(req.packed), flag) is True
            setattr(req, flag, False)
            assert getattr(dns.Message.unpack(req.packed), flag) is False

    def test_copy(self):
        msg = tutils.tdnsresp()
        assert dns.Message.from_state(msg.get_state()) == msg
        copy = msg.copy()
        assert copy is not msg
        assert copy != msg
        copy.id = msg.id
        assert copy == msg
        assert copy.questions is not msg.questions
        assert copy.questions == msg.questions
        assert copy.answers is not msg.answers
        assert copy.answers == msg.answers
        assert copy.authorities is not msg.authorities
        assert copy.authorities == msg.authorities
        assert copy.additionals is not msg.additionals
        assert copy.additionals == msg.additionals


class TestDNSFlow:
    def test_copy(self):
        f = tflow.tdnsflow(resp=True)
        assert repr(f)
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert f is not f2

        assert f.request.get_state() == f2.request.get_state()
        assert f.request is not f2.request
        assert f.request == f2.request
        assert f.response is not f2.response
        assert f.response.get_state() == f2.response.get_state()
        assert f.response == f2.response

        f = tflow.tdnsflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.request is not f2.request
        assert f.request == f2.request
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.tdnsflow(resp=True)
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert flowfilter.match("~b dns.google", f)
        assert flowfilter.match("~b 8.8.8.8", f)

        assert flowfilter.match("~bq dns.google", f)
        assert not flowfilter.match("~bq 8.8.8.8", f)

        assert flowfilter.match("~bs dns.google", f)
        assert flowfilter.match("~bs 8.8.4.4", f)

        assert flowfilter.match("~dns", f)
        assert not flowfilter.match("~dns", tflow.ttcpflow())
        assert not flowfilter.match("~dns", tflow.tflow())

        f = tflow.tdnsflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.tdnsflow()
        assert "DNSFlow" in repr(f)

    def test_question(self):
        r = tflow.tdnsreq()
        assert r.question
        r.questions = []
        assert not r.question
