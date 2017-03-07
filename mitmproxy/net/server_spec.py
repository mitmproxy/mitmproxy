"""
Parse scheme, host and port from a string.
"""
import collections
import re
from typing import Tuple

from mitmproxy.net import check

ServerSpec = collections.namedtuple("ServerSpec", ["scheme", "address"])

server_spec_re = re.compile(
    r"""
        ^
        (?:(?P<scheme>\w+)://)?  # scheme is optional
        (?P<host>[^:/]+|\[.+\])  # hostname can be DNS name, IPv4, or IPv6 address.
        (?::(?P<port>\d+))?  #  port is optional
        /?  #  we allow a trailing backslash, but no path
        $
        """,
    re.VERBOSE
)


def parse(server_spec: str) -> ServerSpec:
    """
    Parses a server mode specification, e.g.:

        - http://example.com/
        - example.org
        - example.com:443

    Raises:
        ValueError, if the server specification is invalid.
    """
    m = server_spec_re.match(server_spec)
    if not m:
        raise ValueError("Invalid server specification: {}".format(server_spec))

    # defaulting to https/port 443 may annoy some folks, but it's secure-by-default.
    scheme = m.group("scheme") or "https"
    if scheme not in ("http", "https"):
        raise ValueError("Invalid server scheme: {}".format(scheme))

    host = m.group("host")
    # IPv6 brackets
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not check.is_valid_host(host.encode("idna")):
        raise ValueError("Invalid hostname: {}".format(host))

    if m.group("port"):
        port = int(m.group("port"))
    else:
        port = {
            "http": 80,
            "https": 443
        }[scheme]
    if not check.is_valid_port(port):
        raise ValueError("Invalid port: {}".format(port))

    return ServerSpec(scheme, (host, port))


def parse_with_mode(mode: str) -> Tuple[str, ServerSpec]:
    """
    Parse a proxy mode specification, which is usually just (reverse|upstream):server-spec

    Returns:
        A (mode, server_spec) tuple.

    Raises:
        ValueError, if the specification is invalid.
    """
    mode, server_spec = mode.split(":", maxsplit=1)
    return mode, parse(server_spec)
