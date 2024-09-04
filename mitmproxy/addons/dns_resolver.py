import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from functools import cache

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
            "Name servers to use for lookups. Default: operating system's name servers",
        )

    def configure(self, updated):
        if "dns_use_hosts_file" in updated or "dns_name_servers" in updated:
            self.resolver.cache_clear()
            self.name_servers.cache_clear()

    @cache
    def name_servers(self) -> list[str]:
        """
        The Operating System name servers,
        or `[]` if they cannot be determined.
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
    def resolver(self) -> mitmproxy_rs.dns.DnsResolver:
        """
        Our mitmproxy_rs DNS resolver.
        """
        ns = self.name_servers()
        assert ns
        return mitmproxy_rs.dns.DnsResolver(
            name_servers=ns,
            use_hosts_file=ctx.options.dns_use_hosts_file,
        )

    async def dns_request(self, flow: dns.DNSFlow) -> None:
        if self._should_resolve(flow):
            all_ip_lookups = (
                flow.request.query
                and flow.request.op_code == dns.op_codes.QUERY
                and flow.request.question
                and flow.request.question.class_ == dns.classes.IN
                and flow.request.question.type in (dns.types.A, dns.types.AAAA)
            )
            name_servers = self.name_servers()

            if all_ip_lookups:
                # For A/AAAA records, we try to use our own resolver
                # (with a fallback to getaddrinfo)
                if name_servers:
                    flow.response = await self.resolve(
                        flow.request, self._with_resolver
                    )
                elif ctx.options.dns_use_hosts_file:
                    # Fallback to getaddrinfo as hickory's resolver isn't as reliable
                    # as we would like it to be (https://github.com/mitmproxy/mitmproxy/issues/7064).
                    flow.response = await self.resolve(
                        flow.request, self._with_getaddrinfo
                    )
                else:
                    flow.error = Error("Cannot resolve, dns_name_servers unknown.")
            elif name_servers:
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
        message: dns.Message,
        resolve_func: Callable[[dns.Question], Awaitable[list[str]]],
    ) -> dns.Message:
        assert message.question
        try:
            ip_addrs = await resolve_func(message.question)
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
                    name=message.question.name,
                    type=message.question.type,
                    class_=message.question.class_,
                    ttl=dns.ResourceRecord.DEFAULT_TTL,
                    data=ipaddress.ip_address(ip).packed,
                )
                for ip in ip_addrs
            ]
        )

    async def _with_resolver(self, question: dns.Question) -> list[str]:
        """Resolve an A/AAAA question using the mitmproxy_rs DNS resolver."""
        if question.type == dns.types.A:
            return await self.resolver().lookup_ipv4(question.name)
        else:
            return await self.resolver().lookup_ipv6(question.name)

    async def _with_getaddrinfo(self, question: dns.Question) -> list[str]:
        """Resolve an A/AAAA question using getaddrinfo."""
        if question.type == dns.types.A:
            family = socket.AF_INET
        else:
            family = socket.AF_INET6
        addrinfos = await asyncio.get_running_loop().getaddrinfo(
            host=question.name,
            port=None,
            family=family,
            type=socket.SOCK_STREAM,
        )
        return [addrinfo[4][0] for addrinfo in addrinfos]
