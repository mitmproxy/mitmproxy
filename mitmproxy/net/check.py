import ipaddress
import re

# Allow underscore in host name
# Note: This could be a DNS label, a hostname, a FQDN, or an IP
_label_valid = re.compile(br"[A-Z\d\-_]{1,63}$", re.IGNORECASE)


def is_valid_host(host: bytes) -> bool:
    """
    Checks if the passed bytes are a valid DNS hostname or an IPv4/IPv6 address.
    """
    try:
        host.decode("idna")
    except ValueError:
        return False
    # RFC1035: 255 bytes or less.
    if len(host) > 255:
        return False
    if host and host[-1:] == b".":
        host = host[:-1]
    # DNS hostname
    if all(_label_valid.match(x) for x in host.split(b".")):
        return True
    # IPv4/IPv6 address
    try:
        ipaddress.ip_address(host.decode('idna'))
        return True
    except ValueError:
        return False


def is_valid_port(port: int) -> bool:
    return 0 <= port <= 65535
