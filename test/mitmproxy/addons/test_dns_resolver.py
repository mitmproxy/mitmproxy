import asyncio
import ipaddress
import socket
from typing import Callable

import pytest

from mitmproxy import dns
from mitmproxy.addons import dns_resolver, proxyserver
from mitmproxy.connection import Address
from mitmproxy.test import taddons, tflow, tutils


async def test_simple(monkeypatch):
    monkeypatch.setattr(
        dns_resolver, "resolve_message", lambda _, __: asyncio.sleep(0, "resp")
    )

    dr = dns_resolver.DnsResolver()
    with taddons.context(dr, proxyserver.Proxyserver()) as tctx:
        f = tflow.tdnsflow()
        await dr.dns_request(f)
        assert f.response

        tctx.options.dns_mode = "reverse:8.8.8.8"
        f = tflow.tdnsflow()
        await dr.dns_request(f)
        assert not f.response


class DummyLoop:
    async def getnameinfo(self, socketaddr: Address, flags: int = 0):
        assert flags == socket.NI_NAMEREQD
        if socketaddr[0] in ("8.8.8.8", "2001:4860:4860::8888"):
            return ("dns.google", "")
        e = socket.gaierror()
        e.errno = socket.EAI_NONAME
        raise e

    async def getaddrinfo(self, host: str, port: int, *, family: int):
        e = socket.gaierror()
        e.errno = socket.EAI_NONAME
        if family == socket.AF_INET:
            if host == "dns.google":
                return [(socket.AF_INET, None, None, None, ("8.8.8.8", port))]
        elif family == socket.AF_INET6:
            if host == "dns.google":
                return [
                    (
                        socket.AF_INET6,
                        None,
                        None,
                        None,
                        ("2001:4860:4860::8888", port, None, None),
                    )
                ]
        else:
            e.errno = socket.EAI_FAMILY
        raise e


async def test_resolve():
    async def fail_with(question: dns.Question, code: int):
        with pytest.raises(dns_resolver.ResolveError) as ex:
            await dns_resolver.resolve_question(question, DummyLoop())
        assert ex.value.response_code == code

    async def succeed_with(
        question: dns.Question, check: Callable[[dns.ResourceRecord], bool]
    ):
        assert any(
            map(check, await dns_resolver.resolve_question(question, DummyLoop()))
        )

    await fail_with(
        dns.Question("dns.google", dns.types.A, dns.classes.CH),
        dns.response_codes.NOTIMP,
    )
    await fail_with(
        dns.Question("not.exists", dns.types.A, dns.classes.IN),
        dns.response_codes.NXDOMAIN,
    )
    await fail_with(
        dns.Question("dns.google", dns.types.SOA, dns.classes.IN),
        dns.response_codes.NOTIMP,
    )
    await fail_with(
        dns.Question("totally.invalid", dns.types.PTR, dns.classes.IN),
        dns.response_codes.FORMERR,
    )
    await fail_with(
        dns.Question("invalid.in-addr.arpa", dns.types.PTR, dns.classes.IN),
        dns.response_codes.FORMERR,
    )
    await fail_with(
        dns.Question("0.0.0.1.in-addr.arpa", dns.types.PTR, dns.classes.IN),
        dns.response_codes.NXDOMAIN,
    )

    await succeed_with(
        dns.Question("dns.google", dns.types.A, dns.classes.IN),
        lambda rr: rr.ipv4_address == ipaddress.IPv4Address("8.8.8.8"),
    )
    await succeed_with(
        dns.Question("dns.google", dns.types.AAAA, dns.classes.IN),
        lambda rr: rr.ipv6_address == ipaddress.IPv6Address("2001:4860:4860::8888"),
    )
    await succeed_with(
        dns.Question("8.8.8.8.in-addr.arpa", dns.types.PTR, dns.classes.IN),
        lambda rr: rr.domain_name == "dns.google",
    )
    await succeed_with(
        dns.Question(
            "8.8.8.8.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.6.8.4.0.6.8.4.1.0.0.2.ip6.arpa",
            dns.types.PTR,
            dns.classes.IN,
        ),
        lambda rr: rr.domain_name == "dns.google",
    )

    req = tutils.tdnsreq()
    req.query = False
    assert (
        await dns_resolver.resolve_message(req, DummyLoop())
    ).response_code == dns.response_codes.REFUSED
    req.query = True
    req.op_code = dns.op_codes.IQUERY
    assert (
        await dns_resolver.resolve_message(req, DummyLoop())
    ).response_code == dns.response_codes.NOTIMP
    req.op_code = dns.op_codes.QUERY
    resp = await dns_resolver.resolve_message(req, DummyLoop())
    assert resp.response_code == dns.response_codes.NOERROR
    assert filter(lambda rr: str(rr.ipv4_address) == "8.8.8.8", resp.answers)
