from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Sequence
from functools import cache
from typing import Protocol

import mitmproxy_rs
from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.flow import Error
from mitmproxy.proxy import mode_specs

logger = logging.getLogger(__name__)


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
            "Name servers to use for lookups in regular DNS mode/wireguard mode. Default: operating system's name servers",
        )

    def configure(self, updated):
        if "dns_use_hosts_file" in updated or "dns_name_servers" in updated:
            self.resolver.cache_clear()
            self.name_servers.cache_clear()

    @cache
    def name_servers(self) -> list[str]:
        """
        Returns the operating system's name servers unless custom name servers are set.
        On error, an empty list is returned.
        """
        try:
            return (
                ctx.options.dns_name_servers
                or mitmproxy_rs.dns.get_system_dns_servers()
            )
        except RuntimeError as e:
            logger.warning(
                f"Failed to get system dns servers: {e}\n"
                f"The dns_name_servers option needs to be set manually."
            )
            return []

    @cache
    def resolver(self) -> Resolver:
        """
        Returns:
            The DNS resolver to use.
        Raises:
            MissingNameServers, if name servers are unknown and `dns_use_hosts_file` is disabled.
        """
        if ns := self.name_servers():
            # We always want to use our own resolver if name server info is available.
            return mitmproxy_rs.dns.DnsResolver(
                name_servers=ns,
                use_hosts_file=ctx.options.dns_use_hosts_file,
            )
        elif ctx.options.dns_use_hosts_file:
            # Fallback to getaddrinfo as hickory's resolver isn't as reliable
            # as we would like it to be (https://github.com/mitmproxy/mitmproxy/issues/7064).
            return GetaddrinfoFallbackResolver()
        else:
            raise MissingNameServers()

    async def dns_request(self, flow: dns.DNSFlow) -> None:
        if self._should_resolve(flow):
            all_ip_lookups = (
                flow.request.query
                and flow.request.op_code == dns.op_codes.QUERY
                and flow.request.question
                and flow.request.question.class_ == dns.classes.IN
                and flow.request.question.type in (dns.types.A, dns.types.AAAA)
            )
            if all_ip_lookups:
                try:
                    flow.response = await self.resolve(flow.request)
                except MissingNameServers:
                    flow.error = Error("Cannot resolve, dns_name_servers unknown.")
            elif name_servers := self.name_servers():
                # For other records, the best we can do is to forward the query
                # to an upstream server.
                flow.server_conn.address = (name_servers[0], 53)
            else:
                flow.error = Error("Cannot resolve, dns_name_servers unknown.")

    @staticmethod
    def _should_resolve(flow: dns.DNSFlow) -> bool:
        return (
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

    async def resolve(
        self,
        message: dns.DNSMessage,
    ) -> dns.DNSMessage:
        q = message.question
        assert q
        try:
            if q.type == dns.types.A:
                ip_addrs = await self.resolver().lookup_ipv4(q.name)
            else:
                ip_addrs = await self.resolver().lookup_ipv6(q.name)
        except socket.gaierror as e:
            match e.args[0]:
                case socket.EAI_NONAME:
                    return message.fail(dns.response_codes.NXDOMAIN)
                case socket.EAI_NODATA:
                    ip_addrs = []
                case _:
                    return message.fail(dns.response_codes.SERVFAIL)

        return message.succeed(
            [
                dns.ResourceRecord(
                    name=q.name,
                    type=q.type,
                    class_=q.class_,
                    ttl=dns.ResourceRecord.DEFAULT_TTL,
                    data=ipaddress.ip_address(ip).packed,
                )
                for ip in ip_addrs
            ]
        )


class Resolver(Protocol):
    async def lookup_ip(self, domain: str) -> list[str]:  # pragma: no cover
        ...

    async def lookup_ipv4(self, domain: str) -> list[str]:  # pragma: no cover
        ...

    async def lookup_ipv6(self, domain: str) -> list[str]:  # pragma: no cover
        ...


class GetaddrinfoFallbackResolver(Resolver):
    async def lookup_ip(self, domain: str) -> list[str]:
        return await self._lookup(domain, socket.AF_UNSPEC)

    async def lookup_ipv4(self, domain: str) -> list[str]:
        return await self._lookup(domain, socket.AF_INET)

    async def lookup_ipv6(self, domain: str) -> list[str]:
        return await self._lookup(domain, socket.AF_INET6)

    async def _lookup(self, domain: str, family: socket.AddressFamily) -> list[str]:
        addrinfos = await asyncio.get_running_loop().getaddrinfo(
            host=domain,
            port=None,
            family=family,
            type=socket.SOCK_STREAM,
        )
        return [addrinfo[4][0] for addrinfo in addrinfos]


class MissingNameServers(RuntimeError):
    pass
