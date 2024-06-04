import base64
import struct
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import IPv6Address

"""
HTTPS records are formatted as follows (as per RFC9460):
- a 2-octet field for SvcPriority as an integer in network byte order.
- the uncompressed, fully qualified TargetName, represented as a sequence of length-prefixed labels per Section 3.1 of [RFC1035].
- the SvcParams, consuming the remainder of the record (so smaller than 65535 octets and constrained by the RDATA and DNS message sizes).

When the list of SvcParams is non-empty, it contains a series of SvcParamKey=SvcParamValue pairs, represented as:
- a 2-octet field containing the SvcParamKey as an integer in network byte order. (See Section 14.3.2 for the defined values.)
- a 2-octet field containing the length of the SvcParamValue as an integer between 0 and 65535 in network byte order.
- an octet string of this length whose contents are the SvcParamValue in a format determined by the SvcParamKey.

    https://datatracker.ietf.org/doc/rfc9460/
    https://datatracker.ietf.org/doc/rfc1035/
"""

MANDATORY = 0
ALPN = 1
NO_DEFAULT_ALPN = 2
PORT = 3
IPV4HINT = 4
ECH = 5
IPV6HINT = 6

_SVCPARAMKEYS = {
    MANDATORY: "mandatory",
    ALPN: "alpn",
    NO_DEFAULT_ALPN: "no-default-alpn",
    PORT: "port",
    IPV4HINT: "ipv4hint",
    ECH: "ech",
    IPV6HINT: "ipv6hint",
}


@dataclass
class SVCParams:
    mandatory: list[int] | None = None
    alpn: list[str] | None = None
    no_default_alpn: bool | None = None
    port: int | None = None
    ipv4hint: list[IPv4Address] | None = None
    ech: str | None = None
    ipv6hint: list[IPv6Address] | None = None

    def __str__(self):
        params = [
            f"mandatory={[_SVCPARAMKEYS.get(i, f'SVCPARAMKEY({i})') for i in self.mandatory]}"
            if self.mandatory is not None
            else "",
            f"alpn={self.alpn}" if self.alpn is not None else "",
            f"no-default-alpn={self.no_default_alpn}"
            if self.no_default_alpn is not None
            else "",
            f"port={self.port}" if self.port is not None else "",
            f"ipv4hint={[str(ip) for ip in self.ipv4hint]}"
            if self.ipv4hint is not None
            else "",
            f'ech="{self.ech}"' if self.ech is not None else "",
            f"ipv6hint={[str(ip) for ip in self.ipv6hint]}"
            if self.ipv6hint is not None
            else "",
        ]
        return " ".join(param for param in params if param)


@dataclass
class HTTPSRecord:
    priority: int
    target_name: str
    params: SVCParams

    def __str__(self):
        return (
            f'priority={self.priority} target_name="{self.target_name}" {self.params}'
        )


def _unpack_params(data: bytes, offset: int) -> SVCParams:
    """Unpacks the service parameters from the given offset."""
    params = SVCParams()
    while offset < len(data):
        param_type = struct.unpack("!H", data[offset : offset + 2])[0]
        offset += 2
        param_length = struct.unpack("!H", data[offset : offset + 2])[0]
        offset += 2
        if offset + param_length > len(data):
            raise struct.error(
                "unpack requires a buffer of %i bytes" % (offset + param_length)
            )
        param_value = data[offset : offset + param_length]
        offset += param_length

        # Interpret parameters based on its type
        if param_type == MANDATORY:
            params.mandatory = [
                struct.unpack("!H", param_value[i : i + 2])[0]
                for i in range(0, param_length, 2)
            ]
        elif param_type == ALPN:
            alpn_protocols = []
            i = 0
            while i < param_length:
                alpn_length = param_value[i]
                i += 1
                try:
                    alpn_protocols.append(
                        param_value[i : i + alpn_length].decode("utf-8")
                    )
                except UnicodeDecodeError:
                    raise struct.error(
                        "unpack encountered illegal characters at offset %i" % (offset)
                    )
                i += alpn_length
            params.alpn = alpn_protocols
        elif param_type == NO_DEFAULT_ALPN:
            params.no_default_alpn = True
        elif param_type == PORT:
            port = struct.unpack("!H", param_value)[0]
            params.port = port
        elif param_type == IPV4HINT:
            params.ipv4hint = [
                IPv4Address(param_value[i : i + 4]) for i in range(0, param_length, 4)
            ]
        elif param_type == ECH:
            ech = base64.b64encode(param_value).decode("utf-8")
            params.ech = ech
        elif param_type == IPV6HINT:
            params.ipv6hint = [
                IPv6Address(param_value[i : i + 16]) for i in range(0, param_length, 16)
            ]
        else:
            raise struct.error(
                f"unknown SVCParamKey {param_type} found in HTTPS record"
            )
    return params


def _unpack_target_name(data: bytes, offset: int) -> tuple[str, int]:
    """Unpacks the DNS-encoded domain name from data starting at the given offset."""
    labels = []
    while True:
        if offset >= len(data):
            raise struct.error("unpack requires a buffer of %i bytes" % offset)
        length = data[offset]
        offset += 1
        if length == 0:
            break
        if offset + length > len(data):
            raise struct.error(
                "unpack requires a buffer of %i bytes" % (offset + length)
            )
        try:
            labels.append(data[offset : offset + length].decode("utf-8"))
        except UnicodeDecodeError:
            raise struct.error(
                "unpack encountered illegal characters at offset %i" % (offset)
            )
        offset += length
    return ".".join(labels), offset


def unpack(data: bytes) -> HTTPSRecord:
    """
    Unpacks HTTPS RDATA from byte data.

    Raises:
        struct.error if the record is malformed.
    """
    offset = 0

    # Priority (2 bytes)
    priority = struct.unpack("!h", data[offset : offset + 2])[0]
    offset += 2

    # TargetName (variable length)
    target_name, offset = _unpack_target_name(data, offset)

    # Service Parameters (remaining bytes)
    params = _unpack_params(data, offset)

    return HTTPSRecord(priority=priority, target_name=target_name, params=params)


def _pack_params(params: SVCParams) -> bytes:
    """Converts the service parameters into the raw byte format"""
    buffer = bytearray()

    if params.mandatory is not None:
        buffer.extend(struct.pack("!H", MANDATORY))
        buffer.extend(struct.pack("!H", len(params.mandatory) * 2))
        for m in params.mandatory:
            buffer.extend(struct.pack("!H", m))

    if params.alpn is not None:
        buffer.extend(struct.pack("!H", ALPN))
        total_len = sum(len(param) + 1 for param in params.alpn)
        buffer.extend(struct.pack("!H", total_len))
        for param in params.alpn:
            buffer.extend(struct.pack("!B", len(param)))
            buffer.extend(param.encode("utf-8"))

    if params.no_default_alpn is not None:
        buffer.extend(struct.pack("!H", NO_DEFAULT_ALPN))
        buffer.extend(struct.pack("!H", 0))

    if params.port is not None:
        buffer.extend(struct.pack("!H", PORT))
        buffer.extend(struct.pack("!H", 2))
        buffer.extend(struct.pack("!H", params.port))

    if params.ipv4hint is not None:
        buffer.extend(struct.pack("!H", IPV4HINT))
        buffer.extend(struct.pack("!H", len(params.ipv4hint) * 4))
        for ipv4 in params.ipv4hint:
            buffer.extend(ipv4.packed)

    if params.ech is not None:
        buffer.extend(struct.pack("!H", ECH))
        ech_bytes = base64.b64decode(params.ech.encode("utf-8"))
        buffer.extend(struct.pack("!H", len(ech_bytes)))
        buffer.extend(ech_bytes)

    if params.ipv6hint is not None:
        buffer.extend(struct.pack("!H", IPV6HINT))
        buffer.extend(struct.pack("!H", len(params.ipv6hint) * 16))
        for ipv6 in params.ipv6hint:
            buffer.extend(ipv6.packed)

    return bytes(buffer)


def _pack_target_name(name: str) -> bytes:
    """Converts the target name into its DNS encoded format"""
    buffer = bytearray()
    for label in name.split("."):
        if len(label) == 0:
            break
        buffer.extend(struct.pack("!B", len(label)))
        buffer.extend(label.encode("utf-8"))
    buffer.extend(struct.pack("!B", 0))
    return bytes(buffer)


def pack(record: HTTPSRecord) -> bytes:
    """Packs the HTTPS record into its bytes form."""
    buffer = bytearray()
    buffer.extend(struct.pack("!h", record.priority))
    buffer.extend(_pack_target_name(record.target_name))
    buffer.extend(_pack_params(record.params))
    return bytes(buffer)
