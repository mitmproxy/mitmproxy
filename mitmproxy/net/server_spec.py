"""
Server specs are used to describe an upstream proxy or server.
"""
import functools
import re
from typing import Tuple, Literal, NamedTuple

from mitmproxy.net import check


class ServerSpec(NamedTuple):
    scheme: Literal["http", "https"]
    address: Tuple[str, int]


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


@functools.lru_cache
def parse(server_spec: str) -> ServerSpec:
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
        scheme = "https" if m.group("port") in ("443", None) else "http"
    if scheme not in ("http", "https"):
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
        port = {
            "http": 80,
            "https": 443
        }[scheme]
    if not check.is_valid_port(port):
        raise ValueError(f"Invalid port: {port}")

    return ServerSpec(scheme, (host, port))  # type: ignore


def parse_with_mode(mode: str) -> Tuple[str, ServerSpec]:
    """
    Parse a proxy mode specification, which is usually just `(reverse|upstream):server-spec`.

    *Raises:*
     - ValueError, if the specification is invalid.
    """
    mode, server_spec = mode.split(":", maxsplit=1)
    return mode, parse(server_spec)
