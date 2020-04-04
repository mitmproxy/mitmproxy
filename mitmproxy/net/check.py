import ipaddress
import re

"""
The rules for host names are different from DNS Names (aka "Label").
DNS Names allow for hyphens and underscores (RFC-2872).
Hostnames DO allow for hyphens, but not underscores. (RFC-952, RFC-1123)
The main issue is the existence of DNS labels that are actually
capable of being resolved to a valid IP, even if the label
isn't a valid hostname (e.g. api-.example.com, @.example.com)

Since the value we're checking could be an IP, a host name, a DNS label, or a FQDN,
and there are cases where DNS or Hostnames are misconfigured despite RFC
we'll go with the least restrictive rules while still providing a sanity check.
"""

# label regex: in total between 4 and 255 chars, tld 2 to 63 chars, each label 1 to 63 chars
_label_valid = re.compile(br"^(?=.{4,255}$)([A-Z0-9_-]([A-Z0-9_-]{0,61}[A-Z0-9_-])?\.){1,126}[A-Z0-9][A-Z0-9-]{0,61}[A-Z0-9]$", re.IGNORECASE)
_host_valid = re.compile(br"[A-Z0-9\-_]{1,63}$", re.IGNORECASE)


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
    # Trim trailing period
    if host and host[-1:] == b".":
        host = host[:-1]
    # DNS label
    if b"." in host and _label_valid.match(host):
        return True
    # hostname
    if b"." not in host and _host_valid.match(host):
        return True
    # IPv4/IPv6 address
    try:
        ipaddress.ip_address(host.decode('idna'))
        return True
    except ValueError:
        return False


def is_valid_port(port: int) -> bool:
    return 0 <= port <= 65535
