from __future__ import annotations
import asyncio
from dataclasses import dataclass
import enum
import ipaddress
import itertools
import random
import socket
import struct
from ipaddress import IPv4Address, IPv6Address
import time
from typing import Any, Callable, Coroutine, Iterable, List, Optional, Tuple, Union

from mitmproxy import connection, flow, stateobject
from mitmproxy.net.dns import domain_names

# DNS parameters taken from https://www.iana.org/assignments/dns-parameters/dns-parameters.xml


class SerializableIntEnum(enum.IntEnum):
    """IntEnum with a minor correction for serialization in tnetstring.py."""

    def __str__(self) -> str:
        return str(self.value)


class CustomValueSerializableIntEnum(SerializableIntEnum):

    @classmethod
    def _missing_(cls, value: object) -> Any:
        assert isinstance(value, int)
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._name_ = str(value)
        return obj


class ResponseCode(SerializableIntEnum):

    _http_equiv: int

    def __new__(cls, value: int, http_equiv: Optional[int] = None) -> ResponseCode:
        # we need this to make mypy happy
        assert http_equiv is not None
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._http_equiv = http_equiv
        return obj

    NOERROR = (0, 200)  # OK
    """No Error [RFC1035]"""
    FORMERR = (1, 400)  # Bad Request
    """Format Error [RFC1035]"""
    SERVFAIL = (2, 500)  # Internal Server Error
    """Server Failure [RFC1035]"""
    NXDOMAIN = (3, 404)  # Not Found
    """Non-Existent Domain [RFC1035]"""
    NOTIMP = (4, 501)  # Not Implemented
    """Not Implemented [RFC1035]"""
    REFUSED = (5, 403)  # Forbidden
    """Query Refused [RFC1035]"""
    YXDOMAIN = (6, 409)  # Conflict
    """Name Exists when it should not [RFC2136 RFC6672]"""
    YXRRSET = (7, 409)  # Conflict
    """RR Set Exists when it should not [RFC2136]"""
    NXRRSET = (8, 410)  # Gone
    """RR Set that should exist does not [RFC2136]"""
    NOTAUTH = (9, 401)  # Unauthorized
    """Server Not Authoritative for zone [RFC2136] | Not Authorized [RFC8945]"""
    NOTZONE = (10, 404)  # Not Found
    """Name not contained in zone [RFC2136]"""
    DSOTYPENI = (11, 501)  # Not Implemented
    """DSO-TYPE Not Implemented [RFC8490]"""

    @property
    def http_equiv_status_code(self) -> int:
        return self._http_equiv


class Type(CustomValueSerializableIntEnum):
    A = 1
    """a host address [RFC1035]"""
    NS = 2
    """an authoritative name server [RFC1035]"""
    MD = 3
    """a mail destination (OBSOLETE - use MX) [RFC1035]"""
    MF = 4
    """a mail forwarder (OBSOLETE - use MX) [RFC1035]"""
    CNAME = 5
    """the canonical name for an alias [RFC1035]"""
    SOA = 6
    """marks the start of a zone of authority [RFC1035]"""
    MB = 7
    """a mailbox domain name (EXPERIMENTAL) [RFC1035]"""
    MG = 8
    """a mail group member (EXPERIMENTAL) [RFC1035]"""
    MR = 9
    """a mail rename domain name (EXPERIMENTAL) [RFC1035]"""
    NULL = 10
    """a null RR (EXPERIMENTAL) [RFC1035]"""
    WKS = 11
    """a well known service description [RFC1035]"""
    PTR = 12
    """a domain name pointer [RFC1035]"""
    HINFO = 13
    """host information [RFC1035]"""
    MINFO = 14
    """mailbox or mail list information [RFC1035]"""
    MX = 15
    """mail exchange [RFC1035]"""
    TXT = 16
    """text strings [RFC1035]"""
    RP = 17
    """for Responsible Person [RFC1183]"""
    AFSDB = 18
    """for AFS Data Base location [RFC1183 RFC5864]"""
    X25 = 19
    """for X.25 PSDN address [RFC1183]"""
    ISDN = 20
    """for ISDN address [RFC1183]"""
    RT = 21
    """for Route Through [RFC1183]"""
    NSAP = 22
    """for NSAP address, NSAP style A record [RFC1706]"""
    NSAP_PTR = 23
    """for domain name pointer, NSAP style [RFC1706]"""
    SIG = 24
    """for security signature [RFC2536 RFC2931 RFC3110 RFC4034]"""
    KEY = 25
    """for security key [RFC2536 RFC2539 RFC3110 RFC4034]"""
    PX = 26
    """X.400 mail mapping information [RFC2163]"""
    GPOS = 27
    """Geographical Position [RFC1712]"""
    AAAA = 28
    """IP6 Address [RFC3596]"""
    LOC = 29
    """Location Information [RFC1876]"""
    NXT = 30
    """Next Domain (OBSOLETE) [RFC2535 RFC3755]"""
    EID = 31
    """Endpoint Identifier [Michael_Patton http://ana-3.lcs.mit.edu/~jnc/nimrod/dns.txt]"""
    NIMLOC = 32
    """Nimrod Locator [1 Michael_Patton http://ana-3.lcs.mit.edu/~jnc/nimrod/dns.txt]"""
    SRV = 33
    """Server Selection [1 RFC2782]"""
    ATMA = 34
    """ATM Address [http://www.broadband-forum.org/ftp/pub/approved-specs/af-dans-0152.000.pdf]"""
    NAPTR = 35
    """Naming Authority Pointer [RFC3403]"""
    KX = 36
    """Key Exchanger [RFC2230]"""
    CERT = 37
    """CERT [RFC4398]"""
    A6 = 38
    """A6 (OBSOLETE - use AAAA) [RFC2874 RFC3226 RFC6563]"""
    DNAME = 39
    """DNAME [RFC6672]"""
    SINK = 40
    """SINK [Donald_E_Eastlake draft-eastlake-kitchen-sink]"""
    OPT = 41
    """OPT [RFC3225 RFC6891]"""
    APL = 42
    """APL [RFC3123]"""
    DS = 43
    """Delegation Signer [RFC4034]"""
    SSHFP = 44
    """SSH Key Fingerprint [RFC4255]"""
    IPSECKEY = 45
    """IPSECKEY [RFC4025]"""
    RRSIG = 46
    """RRSIG [RFC4034]"""
    NSEC = 47
    """NSEC [RFC4034 RFC9077]"""
    DNSKEY = 48
    """DNSKEY [RFC4034]"""
    DHCID = 49
    """DHCID [RFC4701]"""
    NSEC3 = 50
    """NSEC3 [RFC5155 RFC9077]"""
    NSEC3PARAM = 51
    """NSEC3PARAM [RFC5155]"""
    TLSA = 52
    """TLSA [RFC6698]"""
    SMIMEA = 53
    """S/MIME cert association [RFC8162]"""
    HIP = 55
    """Host Identity Protocol [RFC8005]"""
    NINFO = 56
    """NINFO [Jim_Reid]"""
    RKEY = 57
    """RKEY [Jim_Reid]"""
    TALINK = 58
    """Trust Anchor LINK [Wouter_Wijngaards]"""
    CDS = 59
    """Child DS [RFC7344]"""
    CDNSKEY = 60
    """DNSKEY(s) the Child wants reflected in DS [RFC7344]"""
    OPENPGPKEY = 61
    """OpenPGP Key [RFC7929]"""
    CSYNC = 62
    """Child-To-Parent Synchronization [RFC7477]"""
    ZONEMD = 63
    """Message Digest Over Zone Data [RFC8976]"""
    SVCB = 64
    """Service Binding [draft-ietf-dnsop-svcb-https-00]"""
    HTTPS = 65
    """HTTPS Binding [draft-ietf-dnsop-svcb-https-00]"""
    SPF = 99
    """[RFC7208]"""
    UINFO = 100
    """[IANA-Reserved]"""
    UID = 101
    """[IANA-Reserved]"""
    GID = 102
    """[IANA-Reserved]"""
    UNSPEC = 103
    """[IANA-Reserved]"""
    NID = 104
    """[RFC6742]"""
    L32 = 105
    """[RFC6742]"""
    L64 = 106
    """[RFC6742]"""
    LP = 107
    """[RFC6742]"""
    EUI48 = 108
    """an EUI-48 address [RFC7043]"""
    EUI64 = 109
    """an EUI-64 address [RFC7043]"""
    TKEY = 249
    """Transaction Key [RFC2930]"""
    TSIG = 250
    """Transaction Signature [RFC8945]"""
    IXFR = 251
    """incremental transfer [RFC1995]"""
    AXFR = 252
    """transfer of an entire zone [RFC1035 RFC5936]"""
    MAILB = 253
    """mailbox-related RRs (MB, MG or MR) [RFC1035]"""
    MAILA = 254
    """mail agent RRs (OBSOLETE - see MX) [RFC1035]"""
    ANY = 255
    """A request for some or all records the server has available [RFC1035 RFC6895 RFC8482]"""
    URI = 256
    """URI [RFC7553]"""
    CAA = 257
    """Certification Authority Restriction [RFC8659]"""
    AVC = 258
    """Application Visibility and Control [Wolfgang_Riedel]"""
    DOA = 259
    """Digital Object Architecture [draft-durand-doa-over-dns]"""
    AMTRELAY = 260
    """Automatic Multicast Tunneling Relay [RFC8777]"""
    TA = 32768
    """DNSSEC Trust Authorities [Sam_Weiler http://cameo.library.cmu.edu/ http://www.watson.org/~weiler/INI1999-19.pdf]"""
    DLV = 32769
    """DNSSEC Lookaside Validation (OBSOLETE) [RFC8749 RFC4431]"""


class Class(CustomValueSerializableIntEnum):
    IN = 1
    """Internet [RFC1035]"""
    CH = 3
    """Chaos [D. Moon, "Chaosnet", A.I. Memo 628, Massachusetts Institute of Technology Artificial Intelligence Laboratory, June 1981.]"""
    HS = 4
    """Hesiod [Dyer, S., and F. Hsu, "Hesiod", Project Athena Technical Plan - Name Service, April 1987.]"""
    NONE = 254
    """QCLASS NONE [RFC2136]"""
    ANY = 255
    """QCLASS * [RFC1035]"""


class OpCode(SerializableIntEnum):
    QUERY = 0
    """Query [RFC1035]"""
    IQUERY = 1
    """Inverse Query (OBSOLETE) [RFC3425]"""
    STATUS = 2
    """Status [RFC1035]"""
    NOTIFY = 4
    """Notify [RFC1996]"""
    UPDATE = 5
    """Update [RFC2136]"""
    DSO = 6
    """DNS Stateful Operations [RFC8490]"""


class BypassInitStateObject(stateobject.StateObject):
    @classmethod
    def from_state(cls, state):
        obj = cls.__new__(cls)  # `cls(**state)` won't work recursively
        obj.set_state(state)
        return obj


class ResolveError(Exception):
    """Exception thrown by different resolve methods."""
    def __init__(self, response_code: ResponseCode) -> None:
        assert response_code is not ResponseCode.NOERROR
        self.response_code = response_code


@dataclass
class Question(BypassInitStateObject):
    HEADER = struct.Struct("!HH")
    IP4_PTR_SUFFIX = ".in-addr.arpa"
    IP6_PTR_SUFFIX = ".ip6.arpa"

    name: str
    type: Type
    class_: Class

    _stateobject_attributes = dict(name=str, type=Type, class_=Class)

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
                raise ResolveError(ResponseCode.NXDOMAIN)
            else:
                # NOTE might fail on Windows for IPv6 queries:
                # https://stackoverflow.com/questions/66755681/getaddrinfo-c-on-windows-not-handling-ipv6-correctly-returning-error-code-1
                raise ResolveError(ResponseCode.SERVFAIL)
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
            raise ResolveError(ResponseCode.FORMERR)
        try:
            name, _ = await loop.getnameinfo(addr, flags=socket.NI_NAMEREQD)
        except socket.gaierror as e:
            raise ResolveError(ResponseCode.NXDOMAIN if e.errno == socket.EAI_NONAME else ResponseCode.SERVFAIL)
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
        if self.class_ is not Class.IN:
            raise ResolveError(ResponseCode.NOTIMP)
        if self.type is Type.A:
            return self._resolve_by_name(loop, socket.AddressFamily.AF_INET, ipaddress.IPv4Address)
        elif self.type is Type.AAAA:
            return self._resolve_by_name(loop, socket.AddressFamily.AF_INET6, ipaddress.IPv6Address)
        elif self.type is Type.PTR:
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
                raise ResolveError(ResponseCode.FORMERR)
        else:
            raise ResolveError(ResponseCode.NOTIMP)

    def to_json(self) -> dict:
        """
        Converts the question into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "name": self.name,
            "type": self.type.name,
            "class": self.class_.name,
        }


@dataclass
class ResourceRecord(BypassInitStateObject):
    DEFAULT_TTL = 60
    HEADER = struct.Struct("!HHIH")

    name: str
    type: Type
    class_: Class
    ttl: int
    data: bytes

    _stateobject_attributes = dict(name=str, type=Type, class_=Class, ttl=int, data=bytes)

    def __str__(self) -> str:
        try:
            if self.type is Type.A:
                return str(self.ipv4_address)
            if self.type is Type.AAAA:
                return str(self.ipv6_address)
            if self.type in [Type.NS, Type.CNAME, Type.PTR]:
                return self.domain_name
            if self.type is Type.TXT:
                return self.text
        except:
            return f"0x{self.data.hex()} (invalid {self.type.name} data)"
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
            "type": self.type.name,
            "class": self.class_.name,
            "ttl": self.ttl,
            "data": str(self),
        }

    @classmethod
    def A(cls, name: str, ip: IPv4Address, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv4 resource record."""
        return cls(name, Type.A, Class.IN, ttl, ip.packed)

    @classmethod
    def AAAA(cls, name: str, ip: IPv6Address, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv6 resource record."""
        return cls(name, Type.AAAA, Class.IN, ttl, ip.packed)

    @classmethod
    def CNAME(cls, alias: str, canonical: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a canonical internet name resource record."""
        return cls(alias, Type.CNAME, Class.IN, ttl, domain_names.pack(canonical))

    @classmethod
    def PTR(cls, inaddr: str, ptr: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a canonical internet name resource record."""
        return cls(inaddr, Type.PTR, Class.IN, ttl, domain_names.pack(ptr))

    @classmethod
    def TXT(cls, name: str, text: str, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create a textual resource record."""
        return cls(name, Type.TXT, Class.IN, ttl, text.encode("utf-8"))


# comments are taken from rfc1035
@dataclass
class Message(BypassInitStateObject):
    HEADER = struct.Struct("!HHHHHH")

    timestamp: float
    """The time at which the message was sent or received."""
    id: int
    """An identifier assigned by the program that generates any kind of query."""
    query: bool
    """A field that specifies whether this message is a query."""
    op_code: OpCode
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
    response_code: ResponseCode
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
        op_code=OpCode,
        authoritative_answer=bool,
        truncation=bool,
        recursion_desired=bool,
        recursion_available=bool,
        reserved=int,
        response_code=ResponseCode,
        questions=List[Question],
        answers=List[ResourceRecord],
        authorities=List[ResourceRecord],
        additionals=List[ResourceRecord],
    )

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

    def fail(self, response_code: ResponseCode) -> Message:
        if response_code is ResponseCode.NOERROR:
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
            response_code=ResponseCode.NOERROR,
            questions=self.questions,
            answers=answers,
            authorities=[],
            additionals=[],
        )

    async def resolve(self) -> Message:
        """Resolves the message and return the result in form of a response message."""
        try:
            if not self.query:
                raise ResolveError(ResponseCode.REFUSED)  # we cannot resolve an answer
            if self.op_code is not OpCode.QUERY:
                raise ResolveError(ResponseCode.NOTIMP)  # inverse queries and others are not supported
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
                op_code = OpCode((flags >> 11) & 0b1111),
                authoritative_answer=(flags & (1 << 10)) != 0,
                truncation = (flags & (1 << 9)) != 0,
                recursion_desired = (flags & (1 << 8)) != 0,
                recursion_available = (flags & (1 << 7)) != 0,
                reserved = (flags >> 4) & 0b111,
                response_code = ResponseCode(flags & 0b1111),
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
                try:
                    question = Question(name=name, type=Type(type), class_=Class(class_))
                except ValueError as e:
                    raise struct.error(str(e))
                msg.questions.append(question)
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
                    try:
                        rr = ResourceRecord(name, Type(type), Class(class_), ttl, buffer[offset:end_data])
                    except ValueError as e:
                        raise struct.error(str(e))
                    section.append(rr)
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
            raise ValueError(f"DNS message ID {self.id} is out of bound.")
        flags = 0
        if not self.query:
            flags |= 1 << 15
        flags |= self.op_code.value << 11
        if self.authoritative_answer:
            flags |= 1 << 10
        if self.truncation:
            flags |= 1 << 9
        if self.recursion_desired:
            flags |= 1 << 8
        if self.recursion_available:
            flags |= 1 << 7
        if self.reserved < 0 or self.reserved > 7:
            raise ValueError(f"DNS message reserved value {self.reserved} is out of bound.")
        flags |= self.reserved << 4
        flags |= self.response_code.value
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
            data.extend(Question.HEADER.pack(question.type.value, question.class_.value))
        for rr in [*self.answers, *self.authorities, *self.additionals]:
            data.extend(domain_names.pack(rr.name))
            data.extend(ResourceRecord.HEADER.pack(rr.type.value, rr.class_.value, rr.ttl, len(rr.data)))
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
            "op_code": self.op_code.name,
            "authoritative_answer": self.authoritative_answer,
            "truncation": self.truncation,
            "recursion_desired": self.recursion_desired,
            "recursion_available": self.recursion_available,
            "response_code": self.response_code.name,
            "status_code": self.response_code.http_equiv_status_code,
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
    request: Message
    response: Optional[Message] = None

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["request"] = Message
    _stateobject_attributes["response"] = Message

    def __init__(self, client_conn: connection.Client, server_conn: connection.Server):
        super().__init__("dns", client_conn, server_conn, True)

    def __repr__(self) -> str:
        return f"<DNSFlow\r\n  request={repr(self.request)}\r\n  response={repr(self.response)}\r\n>"
