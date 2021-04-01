import ipaddress
import re

# Allow underscore in host name
# Note: This could be a DNS label, a hostname, a FQDN, or an IP
from typing import AnyStr

_label_valid = re.compile(br"[A-Z\d\-_]{1,63}$", re.IGNORECASE)


def is_valid_host(host: AnyStr) -> bool:
    """
    Checks if the passed bytes are a valid DNS hostname or an IPv4/IPv6 address.
    """
    if isinstance(host, str):
        try:
            host_bytes = host.encode("idna")
        except UnicodeError:
            return False
    else:
        host_bytes = host
    try:
        host_bytes.decode("idna")
    except ValueError:
        return False
    # RFC1035: 255 bytes or less.
    if len(host_bytes) > 255:
        return False
    if host_bytes and host_bytes.endswith(b"."):
        host_bytes = host_bytes[:-1]
    # DNS hostname
    if all(_label_valid.match(x) for x in host_bytes.split(b".")):
        return True
    # IPv4/IPv6 address
    try:
        ipaddress.ip_address(host_bytes.decode('idna'))
        return True
    except ValueError:
        return False


def is_valid_port(port: int) -> bool:
    return 0 <= port <= 65535
