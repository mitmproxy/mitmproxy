import socket

import mitmproxy_rs

from mitmproxy import dns
from mitmproxy.addons import dns_resolver
from mitmproxy.addons import proxyserver
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


async def test_ignores_reverse_mode():
    dr = dns_resolver.DnsResolver()
    with taddons.context(dr, proxyserver.Proxyserver()):
        f = tflow.tdnsflow()
        await dr.dns_request(f)
        assert f.response

        f = tflow.tdnsflow()
        f.client_conn.proxy_mode = ProxyMode.parse("reverse:dns://8.8.8.8")
        await dr.dns_request(f)
        assert not f.response


async def test_resolver():
    dr = dns_resolver.DnsResolver()
    with taddons.context(dr) as tctx:
        assert dr.name_servers == mitmproxy_rs.get_system_dns_servers()

        tctx.options.dns_name_servers = ["1.1.1.1"]
        assert dr.name_servers == ["1.1.1.1"]

        res_old = dr.resolver
        tctx.options.dns_use_hosts_file = False
        assert dr.resolver != res_old

        tctx.options.dns_name_servers = ["8.8.8.8"]
        assert dr.name_servers == ["8.8.8.8"]


async def lookup_ipv4(name: str):
    if name == "not.exists":
        raise socket.gaierror("NXDOMAIN")
    elif name == "no.records":
        raise socket.gaierror("NOERROR")
    return ["8.8.8.8"]


async def test_dns_request(monkeypatch):
    monkeypatch.setattr(
        mitmproxy_rs.DnsResolver, "lookup_ipv4", lambda _, name: lookup_ipv4(name)
    )

    resolver = dns_resolver.DnsResolver()
    with taddons.context(resolver) as tctx:

        async def process_questions(questions):
            req = tutils.tdnsreq(questions=questions)
            flow = tflow.tdnsflow(req=req)
            flow.server_conn.address = None
            await resolver.dns_request(flow)
            return flow

        req = tutils.tdnsreq()
        req.op_code = dns.op_codes.IQUERY
        flow = tflow.tdnsflow(req=req)
        flow.server_conn.address = None
        await resolver.dns_request(flow)
        assert flow.server_conn.address[0] == resolver.name_servers[0]

        req.query = False
        req.op_code = dns.op_codes.QUERY
        flow = tflow.tdnsflow(req=req)
        flow.server_conn.address = None
        await resolver.dns_request(flow)
        assert flow.server_conn.address[0] == resolver.name_servers[0]

        flow = await process_questions(
            [
                dns.Question("dns.google", dns.types.AAAA, dns.classes.IN),
                dns.Question("dns.google", dns.types.NS, dns.classes.IN),
            ]
        )
        assert flow.server_conn.address[0] == resolver.name_servers[0]

        flow = await process_questions(
            [
                dns.Question("dns.google", dns.types.AAAA, dns.classes.IN),
                dns.Question("dns.google", dns.types.A, dns.classes.IN),
            ]
        )
        assert flow.server_conn.address is None
        assert flow.response

        flow = tflow.tdnsflow()
        await resolver.dns_request(flow)
        assert flow.server_conn.address == ("address", 22)

        flow = await process_questions(
            [
                dns.Question("not.exists", dns.types.A, dns.classes.IN),
            ]
        )
        assert flow.response.response_code == dns.response_codes.NXDOMAIN

        flow = await process_questions(
            [
                dns.Question("no.records", dns.types.A, dns.classes.IN),
            ]
        )
        assert flow.response.response_code == dns.response_codes.NOERROR
        assert not flow.response.answers

        tctx.options.dns_use_hosts_file = False
        flow = await process_questions(
            [
                dns.Question("dns.google", dns.types.A, dns.classes.IN),
            ]
        )
        assert flow.server_conn.address[0] == resolver.name_servers[0]
