import asyncio
import ipaddress
import socket
from collections.abc import Callable
from collections.abc import Iterable

from mitmproxy import dns
from mitmproxy.proxy import mode_specs

IP4_PTR_SUFFIX = ".in-addr.arpa"
IP6_PTR_SUFFIX = ".ip6.arpa"


class ResolveError(Exception):
    """Exception thrown by different resolve methods."""

    def __init__(self, response_code: int) -> None:
        assert response_code != dns.response_codes.NOERROR
        self.response_code = response_code


async def resolve_question_by_name(
    question: dns.Question,
    loop: asyncio.AbstractEventLoop,
    family: socket.AddressFamily,
    ip: Callable[[str], ipaddress.IPv4Address | ipaddress.IPv6Address],
) -> Iterable[dns.ResourceRecord]:
    try:
        addrinfos = await loop.getaddrinfo(
            host=question.name, port=0, family=family, type=socket.SOCK_STREAM
        )
    except socket.gaierror as e:
        if e.errno == socket.EAI_NONAME:
            raise ResolveError(dns.response_codes.NXDOMAIN)
        else:
            # NOTE might fail on Windows for IPv6 queries:
            # https://stackoverflow.com/questions/66755681/getaddrinfo-c-on-windows-not-handling-ipv6-correctly-returning-error-code-1
            raise ResolveError(dns.response_codes.SERVFAIL)  # pragma: no cover
    return map(
        lambda addrinfo: dns.ResourceRecord(
            name=question.name,
            type=question.type,
            class_=question.class_,
            ttl=dns.ResourceRecord.DEFAULT_TTL,
            data=ip(addrinfo[4][0]).packed,
        ),
        addrinfos,
    )


async def resolve_question_by_addr(
    question: dns.Question,
    loop: asyncio.AbstractEventLoop,
    suffix: str,
    sockaddr: Callable[[list[str]], tuple[str, int] | tuple[str, int, int, int]],
) -> Iterable[dns.ResourceRecord]:
    try:
        addr = sockaddr(question.name[: -len(suffix)].split(".")[::-1])
    except ValueError:
        raise ResolveError(dns.response_codes.FORMERR)
    try:
        name, _ = await loop.getnameinfo(addr, flags=socket.NI_NAMEREQD)
    except socket.gaierror as e:
        raise ResolveError(
            dns.response_codes.NXDOMAIN
            if e.errno == socket.EAI_NONAME
            else dns.response_codes.SERVFAIL
        )
    return [
        dns.ResourceRecord(
            name=question.name,
            type=question.type,
            class_=question.class_,
            ttl=dns.ResourceRecord.DEFAULT_TTL,
            data=dns.domain_names.pack(name),
        )
    ]


async def resolve_question(
    question: dns.Question, loop: asyncio.AbstractEventLoop
) -> Iterable[dns.ResourceRecord]:
    """Resolve the question into resource record(s), throwing ResolveError if an error condition occurs."""

    if question.class_ != dns.classes.IN:
        raise ResolveError(dns.response_codes.NOTIMP)
    if question.type == dns.types.A:
        return await resolve_question_by_name(
            question, loop, socket.AddressFamily.AF_INET, ipaddress.IPv4Address
        )
    elif question.type == dns.types.AAAA:
        return await resolve_question_by_name(
            question, loop, socket.AddressFamily.AF_INET6, ipaddress.IPv6Address
        )
    elif question.type == dns.types.PTR:
        name_lower = question.name.lower()
        if name_lower.endswith(IP4_PTR_SUFFIX):
            return await resolve_question_by_addr(
                question=question,
                loop=loop,
                suffix=IP4_PTR_SUFFIX,
                sockaddr=lambda x: (str(ipaddress.IPv4Address(".".join(x))), 0),
            )
        elif name_lower.endswith(IP6_PTR_SUFFIX):
            return await resolve_question_by_addr(
                question=question,
                loop=loop,
                suffix=IP6_PTR_SUFFIX,
                sockaddr=lambda x: (
                    str(ipaddress.IPv6Address(bytes.fromhex("".join(x)))),
                    0,
                    0,
                    0,
                ),
            )
        else:
            raise ResolveError(dns.response_codes.FORMERR)
    else:
        raise ResolveError(dns.response_codes.NOTIMP)


async def resolve_message(
    message: dns.Message, loop: asyncio.AbstractEventLoop
) -> dns.Message:
    try:
        if not message.query:
            raise ResolveError(
                dns.response_codes.REFUSED
            )  # we cannot resolve an answer
        if message.op_code != dns.op_codes.QUERY:
            raise ResolveError(
                dns.response_codes.NOTIMP
            )  # inverse queries and others are not supported
        rrs: list[dns.ResourceRecord] = []
        for question in message.questions:
            rrs.extend(await resolve_question(question, loop))
    except ResolveError as e:
        return message.fail(e.response_code)
    else:
        return message.succeed(rrs)


class DnsResolver:
    async def dns_request(self, flow: dns.DNSFlow) -> None:
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
            # TODO: We need to handle overly long responses here.
            flow.response = await resolve_message(
                flow.request, asyncio.get_running_loop()
            )
