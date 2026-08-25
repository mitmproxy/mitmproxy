from __future__ import annotations

import base64
import itertools
import random
import struct
import time
from collections.abc import Iterable
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import IPv6Address
from typing import Any
from typing import cast
from typing import ClassVar
from typing import Self

from mitmproxy import flow
from mitmproxy.coretypes import serializable
from mitmproxy.net.dns import classes
from mitmproxy.net.dns import domain_names
from mitmproxy.net.dns import https_records
from mitmproxy.net.dns import op_codes
from mitmproxy.net.dns import response_codes
from mitmproxy.net.dns import types
from mitmproxy.net.dns.https_records import HTTPSRecord
from mitmproxy.net.dns.https_records import HTTPSRecordJSON
from mitmproxy.net.dns.https_records import SVCParamKeys

# DNS parameters taken from https://www.iana.org/assignments/dns-parameters/dns-parameters.xml


@dataclass
class Question(serializable.SerializableDataclass):
    HEADER: ClassVar[struct.Struct] = struct.Struct("!HH")

    name: str
    type: int
    class_: int

    def __str__(self) -> str:
        return self.name

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

    @classmethod
    def from_json(cls, data: dict[str, str]) -> Self:
        return cls(
            name=data["name"],
            type=types.from_str(data["type"]),
            class_=classes.from_str(data["class"]),
        )


@dataclass
class ResourceRecord(serializable.SerializableDataclass):
    DEFAULT_TTL: ClassVar[int] = 60
    HEADER: ClassVar[struct.Struct] = struct.Struct("!HHIH")

    name: str
    type: int
    class_: int
    ttl: int
    data: bytes

    def __str__(self) -> str:
        return str(self._data_json())

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

    @property
    def https_alpn(self) -> tuple[bytes, ...] | None:
        record = https_records.unpack(self.data)
        alpn_bytes = record.params.get(SVCParamKeys.ALPN.value, None)
        if alpn_bytes is not None:
            i = 0
            ret = []
            while i < len(alpn_bytes):
                token_len = alpn_bytes[i]
                ret.append(alpn_bytes[i + 1 : i + 1 + token_len])
                i += token_len + 1
            return tuple(ret)
        else:
            return None

    @https_alpn.setter
    def https_alpn(self, alpn: Iterable[bytes] | None) -> None:
        record = https_records.unpack(self.data)
        if alpn is None:
            record.params.pop(SVCParamKeys.ALPN.value, None)
        else:
            alpn_bytes = b"".join(bytes([len(a)]) + a for a in alpn)
            record.params[SVCParamKeys.ALPN.value] = alpn_bytes
        self.data = https_records.pack(record)

    @property
    def https_ech(self) -> str | None:
        record = https_records.unpack(self.data)
        ech_bytes = record.params.get(SVCParamKeys.ECH.value, None)
        if ech_bytes is not None:
            return base64.b64encode(ech_bytes).decode("utf-8")
        else:
            return None

    @https_ech.setter
    def https_ech(self, ech: str | None) -> None:
        record = https_records.unpack(self.data)
        if ech is None:
            record.params.pop(SVCParamKeys.ECH.value, None)
        else:
            ech_bytes = base64.b64decode(ech.encode("utf-8"))
            record.params[SVCParamKeys.ECH.value] = ech_bytes
        self.data = https_records.pack(record)

    def _data_json(self) -> str | HTTPSRecordJSON:
        try:
            match self.type:
                case types.A:
                    return str(self.ipv4_address)
                case types.AAAA:
                    return str(self.ipv6_address)
                case types.NS | types.CNAME | types.PTR:
                    return self.domain_name
                case types.TXT:
                    return self.text
                case types.HTTPS:
                    return https_records.unpack(self.data).to_json()
                case _:
                    return f"0x{self.data.hex()}"
        except Exception:
            return f"0x{self.data.hex()} (invalid {types.to_str(self.type)} data)"

    def to_json(self) -> dict[str, str | int | HTTPSRecordJSON]:
        """
        Converts the resource record into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        return {
            "name": self.name,
            "type": types.to_str(self.type),
            "class": classes.to_str(self.class_),
            "ttl": self.ttl,
            "data": self._data_json(),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        inst = cls(
            name=data["name"],
            type=types.from_str(data["type"]),
            class_=classes.from_str(data["class"]),
            ttl=data["ttl"],
            data=b"",
        )

        d: str = data["data"]
        try:
            match inst.type:
                case types.A:
                    inst.ipv4_address = IPv4Address(d)
                case types.AAAA:
                    inst.ipv6_address = IPv6Address(d)
                case types.NS | types.CNAME | types.PTR:
                    inst.domain_name = d
                case types.TXT:
                    inst.text = d
                case types.HTTPS:
                    record = HTTPSRecord.from_json(cast(HTTPSRecordJSON, d))
                    inst.data = https_records.pack(record)
                case _:
                    raise ValueError
        except Exception:
            inst.data = bytes.fromhex(d.removeprefix("0x").partition(" (")[0])

        return inst

    @classmethod
    def A(cls, name: str, ip: IPv4Address, *, ttl: int = DEFAULT_TTL) -> ResourceRecord:
        """Create an IPv4 resource record."""
        return cls(name, types.A, classes.IN, ttl, ip.packed)

    @classmethod
    def AAAA(
        cls, name: str, ip: IPv6Address, *, ttl: int = DEFAULT_TTL
    ) -> ResourceRecord:
        """Create an IPv6 resource record."""
        return cls(name, types.AAAA, classes.IN, ttl, ip.packed)

    @classmethod
    def CNAME(
        cls, alias: str, canonical: str, *, ttl: int = DEFAULT_TTL
    ) -> ResourceRecord:
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

    @classmethod
    def HTTPS(
        cls, name: str, record: HTTPSRecord, ttl: int = DEFAULT_TTL
    ) -> ResourceRecord:
        """Create a HTTPS resource record"""
        return cls(name, types.HTTPS, classes.IN, ttl, https_records.pack(record))


# comments are taken from rfc1035
@dataclass
class DNSMessage(serializable.SerializableDataclass):
    HEADER: ClassVar[struct.Struct] = struct.Struct("!HHHHHH")

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
    questions: list[Question]
    """
    The question section is used to carry the "question" in most queries, i.e.
    the parameters that define what is being asked.
    """
    answers: list[ResourceRecord]
    """First resource record section."""
    authorities: list[ResourceRecord]
    """Second resource record section."""
    additionals: list[ResourceRecord]
    """Third resource record section."""

    timestamp: float | None = None
    """The time at which the message was sent or received."""

    def __str__(self) -> str:
        return "\r\n".join(
            map(
                str,
                itertools.chain(
                    self.questions, self.answers, self.authorities, self.additionals
                ),
            )
        )

    @property
    def content(self) -> bytes:
        return self.packed

    @property
    def question(self) -> Question | None:
        """DNS practically only supports a single question at the
        same time, so this is a shorthand for this."""
        if len(self.questions) == 1:
            return self.questions[0]
        return None

    @property
    def size(self) -> int:
        """Returns the cumulative data size of all resource record sections."""
        return sum(
            len(x.data)
            for x in itertools.chain.from_iterable(
                [self.answers, self.authorities, self.additionals]
            )
        )

    def fail(self, response_code: int) -> DNSMessage:
        if response_code == response_codes.NOERROR:
            raise ValueError("response_code must be an error code.")
        return DNSMessage(
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

    def succeed(self, answers: list[ResourceRecord]) -> DNSMessage:
        return DNSMessage(
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

    @classmethod
    def unpack(cls, buffer: bytes, timestamp: float | None = None) -> DNSMessage:
        """Converts the entire given buffer into a DNS message."""
        length, msg = cls.unpack_from(buffer, 0, timestamp)
        if length != len(buffer):
            raise struct.error(f"unpack requires a buffer of {length} bytes")
        return msg

    @classmethod
    def unpack_from(
        cls, buffer: bytes | bytearray, offset: int, timestamp: float | None = None
    ) -> tuple[int, DNSMessage]:
        """Converts the buffer from a given offset into a DNS message and also returns its length."""
        (
            id,
            flags,
            len_questions,
            len_answers,
            len_authorities,
            len_additionals,
        ) = DNSMessage.HEADER.unpack_from(buffer, offset)
        msg = DNSMessage(
            timestamp=timestamp,
            id=id,
            query=(flags & (1 << 15)) == 0,
            op_code=(flags >> 11) & 0b1111,
            authoritative_answer=(flags & (1 << 10)) != 0,
            truncation=(flags & (1 << 9)) != 0,
            recursion_desired=(flags & (1 << 8)) != 0,
            recursion_available=(flags & (1 << 7)) != 0,
            reserved=(flags >> 4) & 0b111,
            response_code=flags & 0b1111,
            questions=[],
            answers=[],
            authorities=[],
            additionals=[],
        )
        offset += DNSMessage.HEADER.size
        cached_names = domain_names.cache()

        def unpack_domain_name() -> str:
            nonlocal buffer, offset, cached_names
            name, length = domain_names.unpack_from_with_compression(
                buffer, offset, cached_names
            )
            offset += length
            return name

        for i in range(0, len_questions):
            try:
                name = unpack_domain_name()
                type, class_ = Question.HEADER.unpack_from(buffer, offset)
                offset += Question.HEADER.size
                msg.questions.append(Question(name=name, type=type, class_=class_))
            except struct.error as e:
                raise struct.error(f"question #{i}: {e}")

        def unpack_rrs(
            section: list[ResourceRecord], section_name: str, count: int
        ) -> None:
            nonlocal buffer, offset
            for i in range(0, count):
                try:
                    name = unpack_domain_name()
                    type, class_, ttl, len_data = ResourceRecord.HEADER.unpack_from(
                        buffer, offset
                    )
                    offset += ResourceRecord.HEADER.size
                    end_data = offset + len_data
                    if len(buffer) < end_data:
                        raise struct.error(
                            f"unpack requires a data buffer of {len_data} bytes"
                        )
                    data = buffer[offset:end_data]

                    if domain_names.record_data_can_have_compression(type):
                        data = domain_names.decompress_from_record_data(
                            buffer, offset, end_data, cached_names
                        )

                    section.append(ResourceRecord(name, type, class_, ttl, data))
                    offset += len_data
                except struct.error as e:
                    raise struct.error(f"{section_name} #{i}: {e}")

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
            raise ValueError(
                f"DNS message's reserved value of {self.reserved} is out of bounds."
            )
        flags |= self.reserved << 4
        if self.response_code < 0 or self.response_code > 0b1111:
            raise ValueError(
                f"DNS message's response_code {self.response_code} is out of bounds."
            )
        flags |= self.response_code
        data = bytearray()
        data.extend(
            DNSMessage.HEADER.pack(
                self.id,
                flags,
                len(self.questions),
                len(self.answers),
                len(self.authorities),
                len(self.additionals),
            )
        )
        # TODO implement compression
        for question in self.questions:
            data.extend(domain_names.pack(question.name))
            data.extend(Question.HEADER.pack(question.type, question.class_))
        for rr in (*self.answers, *self.authorities, *self.additionals):
            data.extend(domain_names.pack(rr.name))
            data.extend(
                ResourceRecord.HEADER.pack(rr.type, rr.class_, rr.ttl, len(rr.data))
            )
            data.extend(rr.data)
        return bytes(data)

    def to_json(self) -> dict:
        """
        Converts the message into json for mitmweb.
        Sync with web/src/flow.ts.
        """
        ret = {
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
        }
        if self.timestamp:
            ret["timestamp"] = self.timestamp
        return ret

    @classmethod
    def from_json(cls, data: Any) -> DNSMessage:
        """Reconstruct a DNS message from JSON."""
        inst = cls(
            id=data["id"],
            query=data["query"],
            op_code=op_codes.from_str(data["op_code"]),
            authoritative_answer=data["authoritative_answer"],
            truncation=data["truncation"],
            recursion_desired=data["recursion_desired"],
            recursion_available=data["recursion_available"],
            reserved=0,
            response_code=response_codes.from_str(data["response_code"]),
            questions=[Question.from_json(x) for x in data["questions"]],
            answers=[ResourceRecord.from_json(x) for x in data["answers"]],
            authorities=[ResourceRecord.from_json(x) for x in data["authorities"]],
            additionals=[ResourceRecord.from_json(x) for x in data["additionals"]],
        )
        if ts := data.get("timestamp"):
            inst.timestamp = ts
        return inst

    def copy(self) -> DNSMessage:
        # we keep the copy semantics but change the ID generation
        state = self.get_state()
        state["id"] = random.randint(0, 65535)
        return DNSMessage.from_state(state)


class DNSFlow(flow.Flow):
    """A DNSFlow is a collection of DNS messages representing a single DNS query."""

    request: DNSMessage
    """The DNS request."""
    response: DNSMessage | None = None
    """The DNS response."""

    def get_state(self) -> serializable.State:
        return {
            **super().get_state(),
            "request": self.request.get_state(),
            "response": self.response.get_state() if self.response else None,
        }

    def set_state(self, state: serializable.State) -> None:
        self.request = DNSMessage.from_state(state.pop("request"))
        self.response = (
            DNSMessage.from_state(r) if (r := state.pop("response")) else None
        )
        super().set_state(state)

    def __repr__(self) -> str:
        return f"<DNSFlow\r\n  request={self.request!r}\r\n  response={self.response!r}\r\n>"
