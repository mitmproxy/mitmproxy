import enum
import struct
from dataclasses import dataclass

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


class SVCParamKeys(enum.Enum):
    MANDATORY = 0
    ALPN = 1
    NO_DEFAULT_ALPN = 2
    PORT = 3
    IPV4HINT = 4
    ECH = 5
    IPV6HINT = 6


@dataclass
class HTTPSRecord:
    priority: int
    target_name: str
    params: dict[int, bytes]

    def __repr__(self):
        params = {}
        for param_type, param_value in self.params.items():
            try:
                name = SVCParamKeys(param_type).name.lower()
            except ValueError:
                name = f"key{param_type}"
            params[name] = param_value
        return f"priority: {self.priority} target_name: '{self.target_name}' {params}"


def _unpack_params(data: bytes, offset: int) -> dict[int, bytes]:
    """Unpacks the service parameters from the given offset."""
    params = {}
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
        params[param_type] = param_value
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


def _pack_params(params: dict[int, bytes]) -> bytes:
    """Converts the service parameters into the raw byte format"""
    buffer = bytearray()

    for k, v in params.items():
        buffer.extend(struct.pack("!H", k))
        buffer.extend(struct.pack("!H", len(v)))
        buffer.extend(v)

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
