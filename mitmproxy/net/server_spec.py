"""
Server specs are used to describe an upstream proxy or server.
"""

import re
from functools import cache
from typing import Literal

from mitmproxy.net import check

ServerSpec = tuple[
    Literal["http", "https", "http3", "tls", "dtls", "tcp", "udp", "dns", "quic"],
    tuple[str, int],
]

server_spec_re = re.compile(
    r"""
        ^
        (?:(?P<scheme>\w+)://)?  # scheme is optional
        (?P<host>[^:/]+|\[.+\])  # hostname can be DNS name, IPv4, or IPv6 address.
        (?::(?P<port>\d+))?  #  port is optional
        /?  #  we allow a trailing backslash, but no path
        $
        """,
    re.VERBOSE,
)


@cache
def parse(server_spec: str, default_scheme: str) -> ServerSpec:
    """
    Parses a server mode specification, e.g.:

     - http://example.com/
     - example.org
     - example.com:443

    *Raises:*
     - ValueError, if the server specification is invalid.
    """
    m = server_spec_re.match(server_spec)
    if not m:
        raise ValueError(f"Invalid server specification: {server_spec}")

    if m.group("scheme"):
        scheme = m.group("scheme")
    else:
        scheme = default_scheme
    if scheme not in (
        "http",
        "https",
        "http3",
        "tls",
        "dtls",
        "tcp",
        "udp",
        "dns",
        "quic",
    ):
        raise ValueError(f"Invalid server scheme: {scheme}")

    host = m.group("host")
    # IPv6 brackets
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not check.is_valid_host(host):
        raise ValueError(f"Invalid hostname: {host}")

    if m.group("port"):
        port = int(m.group("port"))
    else:
        try:
            port = {
                "http": 80,
                "https": 443,
                "quic": 443,
                "http3": 443,
                "dns": 53,
            }[scheme]
        except KeyError:
            raise ValueError(f"Port specification missing.")
    if not check.is_valid_port(port):
        raise ValueError(f"Invalid port: {port}")

    return scheme, (host, port)  # type: ignore
