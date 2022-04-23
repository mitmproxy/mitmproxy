from __future__ import annotations
import asyncio
from dataclasses import dataclass
import ipaddress
import itertools
import random
import socket
import struct
from ipaddress import IPv4Address, IPv6Address
import time
from typing import Any, Callable, Coroutine, Iterable, List, Optional, Tuple, Union

from mitmproxy import connection, flow, stateobject
from mitmproxy.net.dns import classes, domain_names, op_codes, response_codes, types

# DNS parameters taken from https://www.iana.org/assignments/dns-parameters/dns-parameters.xml


class ResolveError(Exception):
    """Exception thrown by different resolve methods."""
    def __init__(self, response_code: int) -> None:
        assert response_code != response_codes.NOERROR
        self.response_code = response_code


@dataclass
class Question(stateobject.StateObject):
    HEADER = struct.Struct("!HH")
    IP4_PTR_SUFFIX = ".in-addr.arpa"
    IP6_PTR_SUFFIX = ".ip6.arpa"

    name: str
    type: int
    class_: int

    _stateobject_attributes = dict(name=str, type=int, class_=int)

    @classmethod
    def from_state(cls, state):
        return cls(**state)

    def __str__(self) -> str:
        return self.name

    async def _resolve_by_name(
        self,
        loop: asyncio.AbstractEventLoop,
        family: socket.AddressFamily,
        ip: Callable[[str], Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]
    ) -> Iterable[ResourceRecord]:
        try:
            addrinfos = await loop.getaddrinfo(host=self.name, port=0, family=family)
        except socket.gaierror as e:
            if e.errno == socket.EAI_NONAME:
                raise ResolveError(response_codes.NXDOMAIN)
            else:
                # NOTE might fail on Windows for IPv6 queries:
                # https://stackoverflow.com/questions/66755681/getaddrinfo-c-on-windows-not-handling-ipv6-correctly-returning-error-code-1
                raise ResolveError(response_codes.SERVFAIL)
        return map(lambda addrinfo: ResourceRecord(
            name=self.name,
            type=self.type,
            class_=self.class_,
            ttl=ResourceRecord.DEFAULT_TTL,
            data=ip(addrinfo[4][0]).packed,
        ), addrinfos)

    async def _resolve_by_addr(
        self,
        loop: asyncio.AbstractEventLoop,
        suffix: str,
        sockaddr: Callable[[List[str]], Union[Tuple[str, int], Tuple[str, int, int, int]]]
    ) -> Iterable[ResourceRecord]:
        try:
            addr = sockaddr(self.name[:-len(suffix)].split(".")[::-1])
        except ValueError:
            raise ResolveError(response_codes.FORMERR)
        try:
            name, _ = await loop.getnameinfo(addr, flags=socket.NI_NAMEREQD)
        except socket.gaierror as e:
            raise ResolveError(response_codes.NXDOMAIN if e.errno == socket.EAI_NONAME else response_codes.SERVFAIL)
        return [ResourceRecord(
            name=self.name,
            type=self.type,
            class_=self.class_,
            ttl=ResourceRecord.DEFAULT_TTL,
            data=domain_names.pack(name),
        )]

    def resolve(self) -> Coroutine[Any, Any, Iterable[ResourceRecord]]:
        """Resolve the question into resource record(s), throwing ResolveError if an error condition occurs."""

        loop = asyncio.get_running_loop()
        if self.class_ != classes.IN:
            raise ResolveError(response_codes.NOTIMP)
        if self.type == types.A:
            return self._resolve_by_name(loop, socket.AddressFamily.AF_INET, ipaddress.IPv4Address)
        elif self.type == types.AAAA:
            return self._resolve_by_name(loop, socket.AddressFamily.AF_INET6, ipaddress.IPv6Address)
        elif self.type == types.PTR:
            name_lower = self.name.lower()
            if name_lower.endswith(Question.IP4_PTR_SUFFIX):
                return self._resolve_by_addr(
                    loop=loop,
                    suffix=Question.IP4_PTR_SUFFIX,
                    sockaddr=lambda x: (str(ipaddress.IPv4Address(".".join(x))), 0)
                )
            elif name_lower.endswith(Question.IP6_PTR_SUFFIX):
                return self._resolve_by_addr(
                    loop=loop,
                    suffix=Question.IP6_PTR_SUFFIX,
                    sockaddr=lambda x: (str(ipaddress.IPv6Address(bytes.fromhex("".join(x)))), 0, 0, 0)
                )
            else:
                raise ResolveError(response_codes.FORMERR)
        else:
            raise ResolveError(response_codes.NOTIMP)

    def to_json(self) -> dict:
        """
        Converts the question into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "name": self.name,
            "type": types.to_str(self.type),
            "class": classes.to_str(self.class_),
        }


@dataclass
class ResourceRecord(stateobject.StateObject):
    DEFAULT_TTL = 60
    HEADER = struct.Struct("!HHIH")

    name: str
    type: int
    class_: int
    ttl: int
    data: bytes

    _stateobject_attributes = dict(name=str, type=int, class_=int, ttl=int, data=bytes)

    @classmethod
    def from_state(cls, state):
        return cls(**state)

    def __str__(self) -> str:
        try:
            if self.type == types.A:
                return str(self.ipv4_address)
            if self.type == types.AAAA:
                return str(self.ipv6_address)
            if self.type in (types.NS, types.CNAME, types.PTR):
                return self.domain_name
            if self.type == types.TXT:
                return self.text
        except:
            return f"0x{self.data.hex()} (invalid {types.to_str(self.type)} data)"
        return f"0x{self.data.hex()}"

    @property
    def text(self) -> str:
        return self.data.decode("utf-8")

    @text.setter
    def text(self, value: str) -> None:
        self.data = value.encode("utf-8")

    @property
    def ipv4_address(self) -> IPv4Address:
        return IPv4Address(self.data)

    @ipv4_address.setter
    def ipv4_address(self, ip: IPv4Address) -> None:
        self.data = ip.packed

    @property
    def ipv6_address(self) -> IPv6Address:
        return IPv6Address(self.data)

    @ipv6_address.setter
    def ipv6_address(self, ip: IPv6Address) -> None:
        self.data = ip.packed

    @property
    def domain_name(self) -> str:
        return domain_names.unpack(self.data)

    @domain_name.setter
    def domain_name(self, name: str) -> None:
        self.data = domain_names.pack(name)

    def to_json(self) -> dict:
        """
        Converts the resource record into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "name": self.name,
            "type": types.to_str(self.type),
            "class": classes.to_str(self.class_),
            "ttl": self.ttl,
            "data": str(self),
        }

    @classmethod
    def A(cls, name: str, ip: IPv4Address, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv4 resource record."""
        return cls(name, types.A, classes.IN, ttl, ip.packed)

    @classmethod
    def AAAA(cls, name: str, ip: IPv6Address, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv6 resource record."""
        return cls(name, types.AAAA, classes.IN, ttl, ip.packed)

    @classmethod
    def CNAME(cls, alias: str, canonical: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a canonical internet name resource record."""
        return cls(alias, types.CNAME, classes.IN, ttl, domain_names.pack(canonical))

    @classmethod
    def PTR(cls, inaddr: str, ptr: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a canonical internet name resource record."""
        return cls(inaddr, types.PTR, classes.IN, ttl, domain_names.pack(ptr))

    @classmethod
    def TXT(cls, name: str, text: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a textual resource record."""
        return cls(name, types.TXT, classes.IN, ttl, text.encode("utf-8"))


# comments are taken from rfc1035
@dataclass
class Message(stateobject.StateObject):
    HEADER = struct.Struct("!HHHHHH")

    timestamp: float
    """The time at which the message was sent or received."""
    id: int
    """An identifier assigned by the program that generates any kind of query."""
    query: bool
    """A field that specifies whether this message is a query."""
    op_code: int
    """
    A field that specifies kind of query in this message.
    This value is set by the originator of a request and copied into the response.
    """
    authoritative_answer: bool
    """
    This field is valid in responses, and specifies that the responding name server
    is an authority for the domain name in question section.
    """
    truncation: bool
    """Specifies that this message was truncated due to length greater than that permitted on the transmission channel."""
    recursion_desired: bool
    """
    This field may be set in a query and is copied into the response.
    If set, it directs the name server to pursue the query recursively.
    """
    recursion_available: bool
    """This field is set or cleared in a response, and denotes whether recursive query support is available in the name server."""
    reserved: int
    """Reserved for future use.  Must be zero in all queries and responses."""
    response_code: int
    """This field is set as part of responses."""
    questions: List[Question]
    """
    The question section is used to carry the "question" in most queries, i.e.
    the parameters that define what is being asked.
    """
    answers: List[ResourceRecord]
    """First resource record section."""
    authorities: List[ResourceRecord]
    """Second resource record section."""
    additionals: List[ResourceRecord]
    """Third resource record section."""

    _stateobject_attributes = dict(
        timestamp=float,
        id=int,
        query=bool,
        op_code=int,
        authoritative_answer=bool,
        truncation=bool,
        recursion_desired=bool,
        recursion_available=bool,
        reserved=int,
        response_code=int,
        questions=List[Question],
        answers=List[ResourceRecord],
        authorities=List[ResourceRecord],
        additionals=List[ResourceRecord],
    )

    @classmethod
    def from_state(cls, state):
        obj = cls.__new__(cls)  # `cls(**state)` won't work recursively
        obj.set_state(state)
        return obj

    def __str__(self) -> str:
        return "\r\n".join(map(str, itertools.chain(self.questions, self.answers, self.authorities, self.additionals)))

    @property
    def content(self) -> bytes:
        """Returns the user-friendly content of all parts as encoded bytes."""
        return str(self).encode()

    @property
    def size(self) -> int:
        """Returns the cumulative data size of all resource record sections."""
        return sum(len(x.data) for x in itertools.chain.from_iterable([self.answers, self.authorities, self.additionals]))

    def fail(self, response_code: int) -> Message:
        if response_code == response_codes.NOERROR:
            raise ValueError("response_code must be an error code.")
        return Message(
            timestamp=time.time(),
            id=self.id,
            query=False,
            op_code=self.op_code,
            authoritative_answer=False,
            truncation=False,
            recursion_desired=self.recursion_desired,
            recursion_available=False,
            reserved=0,
            response_code=response_code,
            questions=self.questions,
            answers=[],
            authorities=[],
            additionals=[],
        )

    def succeed(self, answers: List[ResourceRecord]) -> Message:
        return Message(
            timestamp=time.time(),
            id=self.id,
            query=False,
            op_code=self.op_code,
            authoritative_answer=False,
            truncation=False,
            recursion_desired=self.recursion_desired,
            recursion_available=True,
            reserved=0,
            response_code=response_codes.NOERROR,
            questions=self.questions,
            answers=answers,
            authorities=[],
            additionals=[],
        )

    async def resolve(self) -> Message:
        """Resolves the message and return the result in form of a response message."""
        try:
            if not self.query:
                raise ResolveError(response_codes.REFUSED)  # we cannot resolve an answer
            if self.op_code != op_codes.QUERY:
                raise ResolveError(response_codes.NOTIMP)  # inverse queries and others are not supported
            rrs: List[ResourceRecord] = []
            for q in self.questions:
                rrs.extend(await q.resolve())
        except ResolveError as e:
            return self.fail(e.response_code)
        else:
            return self.succeed(rrs)

    @classmethod
    def unpack(cls, buffer: bytes) -> Message:
        """Converts the entire given buffer into a DNS message."""
        length, msg = cls.unpack_from(buffer, 0)
        if length != len(buffer):
            raise struct.error(f"unpack requires a buffer of {length} bytes")
        return msg

    @classmethod
    def unpack_from(cls, buffer: Union[bytes, bytearray], offset: int) -> Tuple[int, Message]:
        """Converts the buffer from a given offset into a DNS message and also returns its length."""
        id, flags, len_questions, len_answers, len_authorities, len_additionals = Message.HEADER.unpack_from(buffer, offset)
        try:
            msg = Message(
                timestamp=time.time(),
                id=id,
                query=(flags & (1 << 15)) == 0,
                op_code = (flags >> 11) & 0b1111,
                authoritative_answer=(flags & (1 << 10)) != 0,
                truncation = (flags & (1 << 9)) != 0,
                recursion_desired = (flags & (1 << 8)) != 0,
                recursion_available = (flags & (1 << 7)) != 0,
                reserved = (flags >> 4) & 0b111,
                response_code = flags & 0b1111,
                questions=[],
                answers=[],
                authorities=[],
                additionals=[],
            )
        except ValueError as e:
            raise struct.error(str(e))
        offset += Message.HEADER.size
        cached_names = domain_names.cache()

        def unpack_domain_name() -> str:
            nonlocal buffer, offset, cached_names
            name, length = domain_names.unpack_from_with_compression(buffer, offset, cached_names)
            offset += length
            return name

        for i in range(0, len_questions):
            try:
                name = unpack_domain_name()
                type, class_ = Question.HEADER.unpack_from(buffer, offset)
                offset += Question.HEADER.size
                msg.questions.append(Question(name=name, type=type, class_=class_))
            except struct.error as e:
                raise struct.error(f"question #{i}: {str(e)}")

        def unpack_rrs(section: List[ResourceRecord], section_name: str, count: int) -> None:
            nonlocal buffer, offset
            for i in range(0, count):
                try:
                    name = unpack_domain_name()
                    type, class_, ttl, len_data = ResourceRecord.HEADER.unpack_from(buffer, offset)
                    offset += ResourceRecord.HEADER.size
                    end_data = offset + len_data
                    if len(buffer) < end_data:
                        raise struct.error(f"unpack requires a data buffer of {len_data} bytes")
                    section.append(ResourceRecord(name, type, class_, ttl, buffer[offset:end_data]))
                    offset += len_data
                except struct.error as e:
                    raise struct.error(f"{section_name} #{i}: {str(e)}")

        unpack_rrs(msg.answers, "answer", len_answers)
        unpack_rrs(msg.authorities, "authority", len_authorities)
        unpack_rrs(msg.additionals, "additional", len_additionals)
        return (offset, msg)

    @property
    def packed(self) -> bytes:
        """Converts the message into network bytes."""
        if self.id < 0 or self.id > 65535:
            raise ValueError(f"DNS message's id {self.id} is out of bounds.")
        flags = 0
        if not self.query:
            flags |= 1 << 15
        if self.op_code < 0 or self.op_code > 0b1111:
            raise ValueError(f"DNS message's op_code {self.op_code} is out of bounds.")
        flags |= self.op_code << 11
        if self.authoritative_answer:
            flags |= 1 << 10
        if self.truncation:
            flags |= 1 << 9
        if self.recursion_desired:
            flags |= 1 << 8
        if self.recursion_available:
            flags |= 1 << 7
        if self.reserved < 0 or self.reserved > 0b111:
            raise ValueError(f"DNS message's reserved value of {self.reserved} is out of bounds.")
        flags |= self.reserved << 4
        if self.response_code < 0 or self.response_code > 0b1111:
            raise ValueError(f"DNS message's response_code {self.response_code} is out of bounds.")
        flags |= self.response_code
        data = bytearray()
        data.extend(Message.HEADER.pack(
            self.id,
            flags,
            len(self.questions),
            len(self.answers),
            len(self.authorities),
            len(self.additionals),
        ))
        # TODO implement compression
        for question in self.questions:
            data.extend(domain_names.pack(question.name))
            data.extend(Question.HEADER.pack(question.type, question.class_))
        for rr in (*self.answers, *self.authorities, *self.additionals):
            data.extend(domain_names.pack(rr.name))
            data.extend(ResourceRecord.HEADER.pack(rr.type, rr.class_, rr.ttl, len(rr.data)))
            data.extend(rr.data)
        return bytes(data)

    def to_json(self) -> dict:
        """
        Converts the message into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "id": self.id,
            "query": self.query,
            "op_code": op_codes.to_str(self.op_code),
            "authoritative_answer": self.authoritative_answer,
            "truncation": self.truncation,
            "recursion_desired": self.recursion_desired,
            "recursion_available": self.recursion_available,
            "response_code": response_codes.to_str(self.response_code),
            "status_code": response_codes.http_equiv_status_code(self.response_code),
            "questions": [question.to_json() for question in self.questions],
            "answers": [rr.to_json() for rr in self.answers],
            "authorities": [rr.to_json() for rr in self.authorities],
            "additionals": [rr.to_json() for rr in self.additionals],
            "size": self.size,
            "timestamp": self.timestamp,
        }

    def copy(self) -> Message:
        # we keep the copy semantics but change the ID generation
        state = self.get_state()
        state["id"] = random.randint(0, 65535)
        return Message.from_state(state)


class DNSFlow(flow.Flow):
    """A DNSFlow is a collection of DNS messages representing a single DNS query."""

    request: Message
    """The DNS request."""
    response: Optional[Message] = None
    """The DNS response."""

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["request"] = Message
    _stateobject_attributes["response"] = Message

    def __init__(self, client_conn: connection.Client, server_conn: connection.Server):
        super().__init__("dns", client_conn, server_conn, True)

    def __repr__(self) -> str:
        return f"<DNSFlow\r\n  request={repr(self.request)}\r\n  response={repr(self.response)}\r\n>"
