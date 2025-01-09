import asyncio
import socket
import sys
import typing

import pytest

import mitmproxy_rs
from mitmproxy import dns
from mitmproxy.addons import dns_resolver
from mitmproxy.addons import proxyserver
from mitmproxy.addons.dns_resolver import GetaddrinfoFallbackResolver
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


async def test_ignores_reverse_mode():
    dr = dns_resolver.DnsResolver()
    with taddons.context(dr, proxyserver.Proxyserver()):
        f = tflow.tdnsflow()
        f.client_conn.proxy_mode = ProxyMode.parse("dns")
        assert dr._should_resolve(f)

        f.client_conn.proxy_mode = ProxyMode.parse("wireguard")
        f.server_conn.address = ("10.0.0.53", 53)
        assert dr._should_resolve(f)

        f.client_conn.proxy_mode = ProxyMode.parse("reverse:dns://8.8.8.8")
        assert not dr._should_resolve(f)


def _err():
    raise RuntimeError("failed to get name servers")


async def test_name_servers(caplog, monkeypatch):
    dr = dns_resolver.DnsResolver()
    with taddons.context(dr) as tctx:
        assert dr.name_servers() == mitmproxy_rs.dns.get_system_dns_servers()

        tctx.options.dns_name_servers = ["1.1.1.1"]
        assert dr.name_servers() == ["1.1.1.1"]

        monkeypatch.setattr(mitmproxy_rs.dns, "get_system_dns_servers", _err)
        tctx.options.dns_name_servers = []
        assert dr.name_servers() == []
        assert "Failed to get system dns servers" in caplog.text


async def lookup(name: str):
    match name:
        case "ipv4.example.com":
            return ["1.2.3.4"]
        case "ipv6.example.com":
            return ["::1"]
        case "no-a-records.example.com":
            raise socket.gaierror(socket.EAI_NODATA)
        case "no-network.example.com":
            raise socket.gaierror(socket.EAI_AGAIN)
        case _:
            raise socket.gaierror(socket.EAI_NONAME)


async def getaddrinfo(host: str, *_, **__):
    return [[None, None, None, None, [ip]] for ip in await lookup(host)]


Domain = typing.Literal[
    "nxdomain.example.com",
    "no-a-records.example.com",
    "no-network.example.com",
    "txt.example.com",
    "ipv4.example.com",
    "ipv6.example.com",
]
# We use literals here instead of bools because that makes the test easier to parse.
HostsFile = typing.Literal["hosts", "no-hosts"]
NameServers = typing.Literal["nameservers", "no-nameservers"]


@pytest.mark.parametrize("hosts_file", typing.get_args(HostsFile))
@pytest.mark.parametrize("name_servers", typing.get_args(NameServers))
@pytest.mark.parametrize("domain", typing.get_args(Domain))
async def test_lookup(
    domain: Domain, hosts_file: HostsFile, name_servers: NameServers, monkeypatch
):
    if name_servers == "nameservers":
        monkeypatch.setattr(
            mitmproxy_rs.dns, "get_system_dns_servers", lambda: ["8.8.8.8"]
        )
        monkeypatch.setattr(
            mitmproxy_rs.dns.DnsResolver, "lookup_ipv4", lambda _, name: lookup(name)
        )
        monkeypatch.setattr(
            mitmproxy_rs.dns.DnsResolver, "lookup_ipv6", lambda _, name: lookup(name)
        )
    else:
        monkeypatch.setattr(mitmproxy_rs.dns, "get_system_dns_servers", lambda: [])
        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)

    dr = dns_resolver.DnsResolver()
    match domain:
        case "txt.example.com":
            typ = dns.types.TXT
        case "ipv6.example.com":
            typ = dns.types.AAAA
        case _:
            typ = dns.types.A

    with taddons.context(dr) as tctx:
        tctx.options.dns_use_hosts_file = hosts_file == "hosts"
        req = tutils.tdnsreq(
            questions=[
                dns.Question(domain, typ, dns.classes.IN),
            ]
        )
        flow = tflow.tdnsflow(req=req)
        await dr.dns_request(flow)

        match (domain, name_servers, hosts_file):
            case [_, "no-nameservers", "no-hosts"]:
                assert flow.error
            case ["nxdomain.example.com", _, _]:
                assert flow.response.response_code == dns.response_codes.NXDOMAIN
            case ["no-network.example.com", _, _]:
                assert flow.response.response_code == dns.response_codes.SERVFAIL
            case ["no-a-records.example.com", _, _]:
                if sys.platform == "win32":
                    # On Windows, EAI_NONAME and EAI_NODATA are the same constant (11001)...
                    assert flow.response.response_code == dns.response_codes.NXDOMAIN
                else:
                    assert flow.response.response_code == dns.response_codes.NOERROR
                assert not flow.response.answers
            case ["txt.example.com", "nameservers", _]:
                assert flow.server_conn.address == ("8.8.8.8", 53)
            case ["txt.example.com", "no-nameservers", _]:
                assert flow.error
            case ["ipv4.example.com", "nameservers", _]:
                assert flow.response.answers[0].data == b"\x01\x02\x03\x04"
            case ["ipv4.example.com", "no-nameservers", "hosts"]:
                assert flow.response.answers[0].data == b"\x01\x02\x03\x04"
            case ["ipv6.example.com", "nameservers", _]:
                assert (
                    flow.response.answers[0].data
                    == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
                )
            case ["ipv6.example.com", "no-nameservers", "hosts"]:
                assert (
                    flow.response.answers[0].data
                    == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
                )
            case other:
                typing.assert_never(other)


async def test_unspec_lookup(monkeypatch):
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
    assert await GetaddrinfoFallbackResolver().lookup_ip("ipv6.example.com") == ["::1"]
