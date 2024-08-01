import ipaddress
import socket
from collections.abc import Iterable
from collections.abc import Sequence
from functools import cache

import mitmproxy_rs

from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.proxy import mode_specs


class ResolveError(Exception):
    """Exception thrown by different resolve methods."""

    def __init__(self, response_code: int) -> None:
        assert response_code != dns.response_codes.NOERROR
        self.response_code = response_code


class DnsResolver:
    def load(self, loader):
        loader.add_option(
            "dns_use_hosts_file",
            bool,
            True,
            "Use the hosts file for DNS lookups in regular DNS mode/wireguard mode.",
        )

        loader.add_option(
            "dns_name_servers",
            Sequence[str],
            [],
            "Name servers to use for lookups. Default: operating system's name servers",
        )

    def configure(self, updated):
        if "dns_use_hosts_file" in updated or "dns_name_servers" in updated:
            self.resolver.cache_clear()
            self.name_servers.cache_clear()

    @cache
    def resolver(self) -> mitmproxy_rs.DnsResolver:
        return mitmproxy_rs.DnsResolver(
            name_servers=self.name_servers(),
            use_hosts_file=ctx.options.dns_use_hosts_file,
        )

    @cache
    def name_servers(self) -> list[str]:
        try:
            return ctx.options.dns_name_servers or mitmproxy_rs.get_system_dns_servers()
        except RuntimeError as e:
            raise RuntimeError(
                f"Failed to get system dns servers: {e}\nMust set dns_name_servers option to run DNS mode."
            )

    async def dns_request(self, flow: dns.DNSFlow) -> None:
        assert flow.request
        should_resolve = (
            (
                isinstance(flow.client_conn.proxy_mode, mode_specs.DnsMode)
                or (
                    isinstance(flow.client_conn.proxy_mode, mode_specs.WireGuardMode)
                    and flow.server_conn.address == ("10.0.0.53", 53)
                )
            )
            and flow.live
            and not flow.response
            and not flow.error
        )
        if should_resolve:
            all_ip_lookups = (
                flow.request.query
                and flow.request.op_code == dns.op_codes.QUERY
                and all(
                    q.type in (dns.types.A, dns.types.AAAA)
                    and q.class_ == dns.classes.IN
                    for q in flow.request.questions
                )
            )
            # We use `mitmproxy_rs.DnsResolver` if we need to use the hosts file to lookup hostnames(A/AAAA queries only)
            # For other cases we forward it to the specified name server directly.
            if all_ip_lookups and ctx.options.dns_use_hosts_file:
                # TODO: We need to handle overly long responses here.
                flow.response = await self.resolve_message(flow.request)
            elif not flow.server_conn.address:
                flow.server_conn.address = (self.name_servers()[0], 53)

    async def resolve_message(self, message: dns.Message) -> dns.Message:
        try:
            rrs: list[dns.ResourceRecord] = []
            for question in message.questions:
                rrs.extend(await self.resolve_question(question))
        except ResolveError as e:
            return message.fail(e.response_code)
        else:
            return message.succeed(rrs)

    async def resolve_question(
        self, question: dns.Question
    ) -> Iterable[dns.ResourceRecord]:
        assert question.type in (dns.types.A, dns.types.AAAA)

        try:
            if question.type == dns.types.A:
                addrinfos = await self.resolver().lookup_ipv4(question.name)
            elif question.type == dns.types.AAAA:
                addrinfos = await self.resolver().lookup_ipv6(question.name)
        except socket.gaierror as e:
            # We aren't exactly following the RFC here
            # https://datatracker.ietf.org/doc/html/rfc2308#section-2
            if e.args[0] == "NXDOMAIN":
                raise ResolveError(dns.response_codes.NXDOMAIN)
            elif e.args[0] == "NOERROR":
                addrinfos = []
            else:  # pragma: no cover
                raise ResolveError(dns.response_codes.SERVFAIL)

        return map(
            lambda addrinfo: dns.ResourceRecord(
                name=question.name,
                type=question.type,
                class_=question.class_,
                ttl=dns.ResourceRecord.DEFAULT_TTL,
                data=ipaddress.ip_address(addrinfo).packed,
            ),
            addrinfos,
        )
