import asyncio

from mitmproxy import dns
from mitmproxy.addons import dns_resolver, proxyserver
from mitmproxy.test import taddons, tflow


async def test_simple(monkeypatch):
    monkeypatch.setattr(dns.Message, "resolve", lambda _: asyncio.sleep(0, "resp"))

    dr = dns_resolver.DnsResolver()
    with taddons.context(dr, proxyserver.Proxyserver()) as tctx:
        f = tflow.tdnsflow()
        await dr.dns_request(f)
        assert f.response

        tctx.options.dns_mode = "reverse:8.8.8.8"
        f = tflow.tdnsflow()
        await dr.dns_request(f)
        assert not f.response
