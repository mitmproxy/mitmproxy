from __future__ import annotations
from dataclasses import dataclass
import enum
import struct
from ipaddress import IPv4Address, IPv6Address
import time
from typing import Dict, List, Optional, Tuple

from mitmproxy import connection, flow, stateobject

# DNS parameters taken from https://www.iana.org/assignments/dns-parameters/dns-parameters.xml


class ResponseCode(enum.IntEnum):
    NOERROR = 0
    """No Error [RFC1035]"""
    FORMERR = 1
    """Format Error [RFC1035]"""
    SERVFAIL = 2
    """Server Failure [RFC1035]"""
    NXDOMAIN = 3
    """Non-Existent Domain [RFC1035]"""
    NOTIMP = 4
    """Not Implemented [RFC1035]"""
    REFUSED = 5
    """Query Refused [RFC1035]"""
    YXDOMAIN = 6
    """Name Exists when it should not [RFC2136 RFC6672]"""
    YXRRSET = 7
    """RR Set Exists when it should not [RFC2136]"""
    NXRRSET = 8
    """RR Set that should exist does not [RFC2136]"""
    NOTAUTH = 9
    """Server Not Authoritative for zone [RFC2136] | Not Authorized [RFC8945]"""
    NOTZONE = 10
    """Name not contained in zone [RFC2136]"""
    DSOTYPENI = 11
    """DSO-TYPE Not Implemented [RFC8490]"""
    BADVERS = 16
    """Bad OPT Version [RFC6891]"""
    BADSIG = 16
    """TSIG Signature Failure [RFC8945]"""
    BADKEY = 17
    """Key not recognized [RFC8945]"""
    BADTIME = 18
    """Signature out of time window [RFC8945]"""
    BADMODE = 19
    """Bad TKEY Mode [RFC2930]"""
    BADNAME = 20
    """Duplicate key name [RFC2930]"""
    BADALG = 21
    """Algorithm not supported [RFC2930]"""
    BADTRUNC = 22
    """Bad Truncation [RFC8945]"""
    BADCOOKIE = 23
    """Bad/missing Server Cookie [RFC7873]"""


class Type(enum.IntEnum):
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


class Class(enum.IntEnum):
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


class OpCode(enum.IntEnum):
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


@dataclass
class Question(stateobject.StateObject):
    HEADER = struct.Struct("!HH")

    name: str
    type: Type
    class_: Class

    _stateobject_attributes = dict(name=str, type=Type, class_=Class)

    def __str__(self) -> str:
        return self.name


@dataclass
class ResourceRecord(stateobject.StateObject):
    # since preferable every query should go through mitmproxy, keep the TTL as low as possible
    DEFAULT_TTL = 1
    HEADER = struct.Struct("!HHIH")

    name: str
    type: Type
    class_: Class
    ttl: int
    data: bytes

    _stateobject_attributes = dict(name=str, type=Type, class_=Class, ttl=int, data=bytes)

    def __str__(self) -> str:
        value = (
            str(self.ipv4_address) if self.type is Type.A
            else
            str(self.ipv6_address) if self.type is Type.AAAA
            else
            self.domain_name if self.type in [Type.NS, Type.CNAME, Type.PTR]
            else
            self.text if self.type in [Type.TXT]
            else
            None
        )
        return self.data.hex() if value is None else value

    @property
    def text(self) -> Optional[str]:
        try:
            return self.data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @text.setter
    def text(self, value: str) -> None:
        self.data = value.encode("utf-8")

    @property
    def ipv4_address(self) -> Optional[IPv4Address]:
        try:
            return IPv4Address(self.data)
        except ValueError:
            return None

    @ipv4_address.setter
    def ipv4_address(self, ip: IPv4Address) -> None:
        self.data = ip.packed

    @property
    def ipv6_address(self) -> Optional[IPv6Address]:
        try:
            return IPv6Address(self.data)
        except ValueError:
            return None

    @ipv6_address.setter
    def ipv6_address(self, ip: IPv6Address) -> None:
        self.data = ip.packed

    @property
    def domain_name(self) -> Optional[str]:
        try:
            return ResourceRecord.unpack_domain_name(self.data)
        except struct.error:
            return None

    @domain_name.setter
    def domain_name(self, name: str) -> None:
        self.data = ResourceRecord.pack_domain_name(name)

    def to_json(self) -> dict:
        """
        Converts the resource record into json for the mitmweb.
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
    def pack_domain_name(cls, name: str) -> bytes:
        """Converts a domain name into RDATA without pointer compression."""
        buffer = bytearray()
        for part in name.split("."):
            label = part.encode("idna")
            size = len(label)
            if size == 0 or size >= 64:
                raise ValueError()
            buffer.append(Message.LABEL_SIZE.pack(size))
            buffer.append(label)
        buffer.append(Message.LABEL_SIZE.pack(0))
        return bytes(buffer)

    @classmethod
    def unpack_domain_name(cls, buffer: bytes) -> str:
        offset = 0
        labels = []
        while True:
            size = Message.LABEL_SIZE.unpack_from(buffer, offset)
            if size & Message.POINTER_INDICATOR == Message.POINTER_INDICATOR:
                raise struct.error(f"unpack encountered a pointer which is not supported in RDATA")
            elif size >= 64:
                raise struct.error(f"unpack encountered a label of length {size}")
            elif size == 0:
                break
            else:
                offset += Message.LABEL_SIZE.size
                end_label = offset + size
                if len(buffer) < end_label:
                    raise struct.error(f"unpack requires a label buffer of {size} bytes")
                labels.append(buffer[range(offset, end_label)].decode("idna"))
                offset += size
        return ".".join(labels)

    @classmethod
    def A(cls, name: str, ip: IPv4Address, *, ttl = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv4 resource record."""
        return ResourceRecord(name, Type.A, Class.IN, ttl, ip.packed)

    @classmethod
    def AAAA(cls, name: str, ip: IPv6Address, *, ttl = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv6 resource record."""
        return ResourceRecord(name, Type.AAAA, Class.IN, ttl, ip.packed)

    @classmethod
    def CNAME(cls, alias: str, canonical: str, *, ttl = DEFAULT_TTL) -> ResourceRecord:
        """Create a canonical internet name resource record."""
        return ResourceRecord(alias, Type.CNAME, Class.IN, ttl, ResourceRecord.encode_domain_name(canonical))


# comments are taken from rfc1035
@dataclass
class Message(stateobject.StateObject):
    HEADER = struct.Struct("!HHHHHH")
    LABEL_SIZE = struct.Struct("!B")
    POINTER_OFFSET = struct.Struct("!H")
    POINTER_INDICATOR = 0b11000000

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
        id=str,
        query=bool,
        op_code=OpCode,
        authoritative_answer=bool,
        truncated=bool,
        recursion_desired=bool,
        recursion_available=bool,
        reserved=int,
        response_code=ResponseCode,
        answers=List[ResourceRecord],
        authorities=List[ResourceRecord],
        additionals=List[ResourceRecord],
    )

    def __str__(self) -> str:
        return "\n".join([str(x) for x in [*self.questions, *self.answers, *self.authorities, *self.additionals]])

    @property
    def size(self) -> int:
        """Returns the cumulative data size of all resource record sections."""
        return sum(len(x.data) for x in [*self.answers, *self.authorities, *self.additionals])

    def fail(self, response_code: ResponseCode) -> Message:
        assert self.query
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
        assert self.query
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

    @classmethod
    def unpack(cls, buffer: bytes) -> Message:
        """Converts the entire given buffer into a DNS message."""
        offset = 0
        id, flags, len_questions, len_answers, len_authorities, len_additionals = Message.HEADER.unpack_from(buffer, offset)
        try:
            msg = Message(
                timestamp=time.time(),
                id=id,
                query=(flags & (1 << 14)) != 0,
                op_code = OpCode((flags >> 11) & 0b1111),
                authoritative_answer=(flags & (1 << 10)) != 0,
                truncation = (flags & (1 << 9)) != 0,
                recursion_desired = (flags & (1 << 8)) != 0,
                recursion_available = (flags & (1 << 7)) != 0,
                reserved = (flags >> 6) & 0b111,
                response_code = ResponseCode(flags & 0b1111),
            )
        except ValueError as e:
            raise struct.error(str(e))
        offset += Message.HEADER.size
        labels: Dict[int, Optional[Tuple[str, int]]] = dict()

        def unpack_domain_name() -> str:
            nonlocal buffer, offset

            def unpack_domain_name_internal(offset: int) -> Tuple[str, int]:
                nonlocal labels, buffer

                if offset in labels:
                    result = labels[offset]
                    if result is None:
                        raise struct.error(f"unpack encountered domain name loop")
                else:
                    labels[offset] = None
                    labels = []
                    length = 0
                    while True:
                        size = Message.LABEL_SIZE.unpack_from(buffer, offset)
                        if size & Message.POINTER_INDICATOR == Message.POINTER_INDICATOR:
                            pointer = Message.POINTER_OFFSET.unpack_from(buffer, offset)
                            length += Message.POINTER_OFFSET.size
                            label, _ = unpack_domain_name_internal(pointer & ~(Message.POINTER_INDICATOR << 8))
                            labels.append(label)
                            break
                        elif size >= 64:
                            raise struct.error(f"unpack encountered a label of length {size}")
                        elif size == 0:
                            length += Message.LABEL_SIZE.size
                            break
                        else:
                            offset += Message.LABEL_SIZE.size
                            end_label = offset + size
                            if len(buffer) < end_label:
                                raise struct.error(f"unpack requires a label buffer of {size} bytes")
                            labels.append(buffer[range(offset, end_label)].decode("idna"))
                            offset += size
                            length += Message.LABEL_SIZE.size + size
                    result = ".".join(labels), length
                    labels[offset] = result
                return result

            name, length = unpack_domain_name_internal(offset)
            offset += length
            return name

        for i in range(1, len_questions):
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

        def unpack_rrs(section: List[ResourceRecord], section_name: str, count: int) -> int:
            nonlocal buffer, offset
            for i in range(1, count):
                try:
                    name = unpack_domain_name()
                    type, class_, ttl, len_data = ResourceRecord.HEADER.unpack_from(buffer, offset)
                    offset += ResourceRecord.HEADER.size
                    end_data = offset + len_data
                    if len(buffer) < end_data:
                        raise struct.error(f"unpack requires a data buffer of {len_data} bytes")
                    try:
                        rr = ResourceRecord(name, Type(type), Class(class_), ttl, buffer[range(offset, end_data)])
                    except ValueError as e:
                        raise struct.error(str(e))
                    section.append(rr)
                    offset += len_data
                except struct.error as e:
                    raise struct.error(f"{section_name} #{i}: {str(e)}")

        unpack_rrs(msg.answers, "answer", len_answers)
        unpack_rrs(msg.authorities, "authority", len_authorities)
        unpack_rrs(msg.additionals, "additional", len_additionals)
        if offset != len(buffer):
            raise struct.error(f"unpack requires a buffer of {offset} bytes")
        return msg

    @property
    def packed(self) -> bytes:
        """Converts the message into network bytes."""
        if id < 0 or id > 65536:
            raise ValueError(f"DNS message ID {self.id} is out of bound.")
        flags = 0
        if self.query:
            flags |= 1 << 14
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
        flags |= self.reserved << 6
        flags |= self.response_code.value
        data = bytearray()
        data.append(Message.HEADER.pack(
            self.id,
            flags,
            len(self.questions),
            len(self.answers),
            len(self.authorities),
            len(self.additionals),
        ))
        # TODO implement compression
        for question in self.questions:
            data.append(ResourceRecord.pack_domain_name(question.name))
            data.append(Question.HEADER.pack(question.type.value, question.class_.value))
        for rr in *self.answers, *self.authorities, *self.additionals:
            data.append(ResourceRecord.pack_domain_name(rr.name))
            data.append(ResourceRecord.HEADER.pack(rr.type.value, rr.class_.value, rr.ttl, len(rr.data)))
            data.append(rr.data)
        return bytes(data)

    def to_json(self) -> dict:
        """
        Converts the message into json for the mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "id": self.id,
            "query": self.query,
            "opCode": self.op_code.name,
            "authoritativeAnswer": self.authoritative_answer,
            "truncation": self.truncation,
            "recursionDesired": self.recursion_desired,
            "recursionAvailable": self.recursion_available,
            "responseCode": self.response_code.name,
            "questions": [{
                "name": question.name,
                "type": question.type.name,
                "class": question.class_.name,
            } for question in self.questions],
            "answers": [rr.to_json() for rr in self.answers],
            "authorities": [rr.to_json() for rr in self.authorities],
            "additionals": [rr.to_json() for rr in self.additionals],
            "size": self.size,
            "timestamp": self.timestamp,
        }


class DNSFlow(flow.Flow):
    request: Message
    response: Optional[Message]

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["request"] = Message
    _stateobject_attributes["response"] = Optional[Message]

    def __init__(self, client_conn: connection.Client, server_conn: connection.Server, live: bool):
        super().__init__("dns", client_conn, server_conn, live)

    def __repr__(self) -> str:
        return f"<DNSFlow\r\n  request={repr(self.request)}\r\n  response={repr(self.response)}\r\n>"
