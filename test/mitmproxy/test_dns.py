import ipaddress
import platform
import struct
from typing import Callable
import pytest

from mitmproxy import dns
from mitmproxy import flowfilter
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestResourceRecord:

    def test_str(self):
        assert str(dns.ResourceRecord.A("test", ipaddress.IPv4Address("1.2.3.4"))) == "1.2.3.4"
        assert str(dns.ResourceRecord.AAAA("test", ipaddress.IPv6Address("::1"))) == "::1"
        assert str(dns.ResourceRecord.CNAME("test", "some.other.host")) == "some.other.host"
        assert str(dns.ResourceRecord.PTR("test", "some.other.host")) == "some.other.host"
        assert str(dns.ResourceRecord.TXT("test", "unicode text 😀")) == "unicode text 😀"
        assert str(dns.ResourceRecord("test", dns.Type.A, dns.Class.IN, dns.ResourceRecord.DEFAULT_TTL, b'')) == "0x (invalid A data)"
        assert str(
            dns.ResourceRecord("test", dns.Type.SOA, dns.Class.IN, dns.ResourceRecord.DEFAULT_TTL, b'\x00\x01\x02\x03')
        ) == "0x00010203"

    def test_setter(self):
        rr = dns.ResourceRecord("test", dns.Type.ANY, dns.Class.IN, dns.ResourceRecord.DEFAULT_TTL, b'')
        rr.ipv4_address = ipaddress.IPv4Address("8.8.4.4")
        assert rr.ipv4_address == ipaddress.IPv4Address("8.8.4.4")
        rr.ipv6_address = ipaddress.IPv6Address("2001:4860:4860::8844")
        assert rr.ipv6_address == ipaddress.IPv6Address("2001:4860:4860::8844")
        rr.domain_name = "www.example.org"
        assert rr.domain_name == "www.example.org"
        rr.text = "sample text"
        assert rr.text == "sample text"


class TestQuestion:

    @pytest.mark.asyncio
    async def test_resolve(self):
        async def fail_with(question: dns.Question, code: dns.ResponseCode):
            with pytest.raises(dns.ResolveError) as ex:
                await question.resolve()
            assert ex.value.response_code == code

        async def succeed_with(question: dns.Question, check: Callable[[dns.ResourceRecord], bool]):
            assert any(map(check, await question.resolve()))

        await fail_with(dns.Question("dns.google", dns.Type.A, dns.Class.CH), dns.ResponseCode.NOTIMP)
        await fail_with(dns.Question("not.exists", dns.Type.A, dns.Class.IN), dns.ResponseCode.NXDOMAIN)
        await fail_with(dns.Question("dns.google", dns.Type.SOA, dns.Class.IN), dns.ResponseCode.NOTIMP)
        await fail_with(dns.Question("totally.invalid", dns.Type.PTR, dns.Class.IN), dns.ResponseCode.FORMERR)
        await fail_with(dns.Question("invalid.in-addr.arpa", dns.Type.PTR, dns.Class.IN), dns.ResponseCode.FORMERR)
        await fail_with(dns.Question("0.0.0.1.in-addr.arpa", dns.Type.PTR, dns.Class.IN), dns.ResponseCode.NXDOMAIN)

        await succeed_with(
            dns.Question("dns.google", dns.Type.A, dns.Class.IN),
            lambda rr: rr.ipv4_address == ipaddress.IPv4Address("8.8.8.8")
        )
        if platform.system() == "Linux":  # will fail on Windows, apparently returns empty on Mac
            await succeed_with(
                dns.Question("dns.google", dns.Type.AAAA, dns.Class.IN),
                lambda rr: rr.ipv6_address == ipaddress.IPv6Address("2001:4860:4860::8888")
            )
        await succeed_with(
            dns.Question("8.8.8.8.in-addr.arpa", dns.Type.PTR, dns.Class.IN),
            lambda rr: rr.domain_name == "dns.google"
        )
        await succeed_with(
            dns.Question("8.8.8.8.in-addr.arpa", dns.Type.PTR, dns.Class.IN),
            lambda rr: rr.domain_name == "dns.google"
        )
        await succeed_with(
            dns.Question("8.8.8.8.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.6.8.4.0.6.8.4.1.0.0.2.ip6.arpa", dns.Type.PTR, dns.Class.IN),
            lambda rr: rr.domain_name == "dns.google"
        )


class TestMessage:

    @pytest.mark.asyncio
    async def test_resolve(self):
        req = tutils.tdnsreq()
        req.query = False
        assert (await req.resolve()).response_code == dns.ResponseCode.REFUSED
        req.query = True
        req.op_code = dns.OpCode.IQUERY
        assert (await req.resolve()).response_code == dns.ResponseCode.NOTIMP
        req.op_code = dns.OpCode.QUERY
        resp = await req.resolve()
        assert resp.response_code == dns.ResponseCode.NOERROR
        assert filter(lambda rr: str(rr.ipv4_address) == "8.8.8.8", resp.answers)

    def test_responses(self):
        req = tutils.tdnsreq()
        resp = tutils.tdnsresp()
        resp2 = req.succeed([
            dns.ResourceRecord.A("dns.google", ipaddress.IPv4Address("8.8.8.8"), ttl=32),
            dns.ResourceRecord.A("dns.google", ipaddress.IPv4Address("8.8.4.4"), ttl=32)
        ])
        resp2.timestamp = resp.timestamp
        assert resp == resp2
        assert resp2.size == 8
        with pytest.raises(ValueError):
            req.fail(dns.ResponseCode.NOERROR)
        assert req.fail(dns.ResponseCode.FORMERR).response_code == dns.ResponseCode.FORMERR

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

        test("id", 0, 2 ** 16 - 1)
        test("reserved", 0, 7)

    def test_packing(self):
        def assert_eq(m: dns.Message, b: bytes) -> None:
            m_b = dns.Message.unpack(b)
            m_b.timestamp = m.timestamp
            assert m_b == m
            assert m_b.packed == m.packed

        assert_eq(tutils.tdnsreq(), b'\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01')
        with pytest.raises(struct.error):
            dns.Message.unpack(b'\x00\x2a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01\x00')
        assert_eq(tutils.tdnsresp(), (
            b'\x00\x2a\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00\x03dns\x06google\x00\x00\x01\x00\x01' +
            b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x08\x08\xc0\x0c\x00\x01\x00\x01\x00\x00\x00 \x00\x04\x08\x08\x04\x04'
        ))

        req = tutils.tdnsreq()
        for flag in "authoritative_answer", "truncation", "recursion_desired", "recursion_available":
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
        assert 'DNSFlow' in repr(f)
