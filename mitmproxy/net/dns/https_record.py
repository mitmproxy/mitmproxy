import base64
import ipaddress
import struct


def _unpack_params(data: bytes, offset: int) -> dict:
    """Unpacks the service parameters from the given offset."""
    params = {}
    while offset < len(data):
        param_type = struct.unpack("!H", data[offset : offset + 2])[0]
        offset += 2
        param_length = struct.unpack("!H", data[offset : offset + 2])[0]
        offset += 2
        param_value = data[offset : offset + param_length]
        offset += param_length

        # Interpret parameters based on its type
        if param_type == 0:  # Mandatory
            mandatory_types = [
                struct.unpack("!H", param_value[i : i + 2])[0]
                for i in range(0, param_length, 2)
            ]
            params["mandatory"] = mandatory_types
        elif param_type == 1:  # ALPN
            alpn_protocols = []
            i = 0
            while i < param_length:
                alpn_length = param_value[i]
                i += 1
                alpn_protocols.append(param_value[i : i + alpn_length].decode("utf-8"))
                i += alpn_length
            params["alpn"] = alpn_protocols
        elif param_type == 2:  # NoDefaultAlpn
            params["no_default_alpn"] = True
        elif param_type == 3:  # Port
            port = struct.unpack("!H", param_value)[0]
            params["port"] = port
        elif param_type == 4:  # IPv4Hint
            ipv4_addresses = [
                str(ipaddress.IPv4Address(param_value[i : i + 4]))
                for i in range(0, param_length, 4)
            ]
            params["ipv4hint"] = ipv4_addresses
        elif param_type == 5:  # ECHConfig
            ech_config = base64.b64encode(param_value).decode("utf-8")
            params["echconfig"] = ech_config
        elif param_type == 6:  # IPv6Hint
            ipv6_addresses = [
                str(ipaddress.IPv6Address(param_value[i : i + 16]))
                for i in range(0, param_length, 16)
            ]
            params["ipv6hint"] = ipv6_addresses
        else:
            params[param_type] = param_value
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
        labels.append(data[offset : offset + length].decode("utf-8"))
        offset += length
    return ".".join(labels), offset


def unpack(data: bytes) -> dict:
    """Unpacks HTTPS RDATA from byte data."""
    offset = 0

    # Priority (2 bytes)
    priority = struct.unpack("!H", data[offset : offset + 2])[0]
    offset += 2

    # TargetName (variable length)
    target_name, offset = _unpack_dns_name(data, offset)

    # Service Parameters (remaining bytes)
    params = _unpack_params(data, offset)

    return {"priority": priority, "target_name": target_name, "params": params}


# def pack(record: dict) -> bytes:
#     """Packs the HTTPS record into its bytes form."""
#     raise NotImplementedError
