import base64
import struct
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import IPv6Address

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
    mandatory: list[str | None] | None = None
    alpn: list[str] | None = None
    no_default_alpn: bool | None = None
    port: int | None = None
    ipv4hint: list[IPv4Address] | None = None
    ech: str | None = None
    ipv6hint: list[IPv6Address] | None = None

    def __str__(self):
        params = [
            f"mandatory={self.mandatory}" if self.mandatory is not None else "",
            f"alpn={self.alpn}" if self.alpn is not None else "",
            f"no-default-alpn={self.no_default_alpn}"
            if self.no_default_alpn is not None
            else "",
            f"port={self.port}" if self.port is not None else "",
            f"ipv4hint={[str(ip) for ip in self.ipv4hint]}"
            if self.ipv4hint is not None
            else "",
            f"ech={self.ech}" if self.ech is not None else "",
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
                "Unpack requires a buffer of %i bytes" % (offset + param_length)
            )
        param_value = data[offset : offset + param_length]
        offset += param_length

        # Interpret parameters based on its type
        if param_type == MANDATORY:
            mandatory_types = [
                struct.unpack("!H", param_value[i : i + 2])[0]
                for i in range(0, param_length, 2)
            ]
            params.mandatory = [_SVCPARAMKEYS.get(i) for i in mandatory_types]
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
                        "Unpack encountered illegal characters at offset %i" % (offset)
                    )
                i += alpn_length
            params.alpn = alpn_protocols
        elif param_type == NO_DEFAULT_ALPN:
            params.no_default_alpn = True
        elif param_type == PORT:
            port = struct.unpack("!H", param_value)[0]
            params.port = port
        elif param_type == IPV4HINT:
            try:
                ipv4_addresses = [
                    IPv4Address(param_value[i : i + 4])
                    for i in range(0, param_length, 4)
                ]
            except ValueError:
                raise struct.error("Malformed IP address found in HTTPS record")
            params.ipv4hint = ipv4_addresses
        elif param_type == ECH:
            ech = base64.b64encode(param_value).decode("utf-8")
            params.ech = ech
        elif param_type == IPV6HINT:
            try:
                ipv6_addresses = [
                    IPv6Address(param_value[i : i + 16])
                    for i in range(0, param_length, 16)
                ]
            except ValueError:
                raise struct.error("Malformed IP address found in HTTPS record")
            params.ipv6hint = ipv6_addresses
        else:
            raise struct.error("Unknown SVCParamKey found in HTTPS record")
    return params


def _unpack_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Unpacks the DNS-encoded domain name from data starting at the given offset."""
    labels = []
    while True:
        length = data[offset]
        if length == 0:
            offset += 1
            break
        offset += 1
        if offset + length > len(data):
            raise struct.error(
                "Unpack requires a buffer of %i bytes" % (offset + length)
            )
        try:
            labels.append(data[offset : offset + length].decode("utf-8"))
        except UnicodeDecodeError:
            raise struct.error(
                "Unpack encountered illegal characters at offset %i" % (offset)
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
    priority = struct.unpack("!H", data[offset : offset + 2])[0]
    offset += 2

    # TargetName (variable length)
    target_name, offset = _unpack_dns_name(data, offset)

    # Service Parameters (remaining bytes)
    params = _unpack_params(data, offset)

    return HTTPSRecord(priority=priority, target_name=target_name, params=params)


# def pack(record: dict) -> bytes:
#     """Packs the HTTPS record into its bytes form."""
#     raise NotImplementedError
