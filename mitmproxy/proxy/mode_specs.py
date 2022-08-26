"""
This module defines all built-in mode specifications.
"""

from typing import Literal

from mitmproxy.net import server_spec
from mitmproxy.proxy import layers
from mitmproxy.proxy.mode import AsyncioProxyMode


TCP: Literal['tcp', 'udp'] = "tcp"
UDP: Literal['tcp', 'udp'] = "udp"


def _check_empty(data):
    if data:
        raise ValueError("mode takes no arguments")


class RegularMode(AsyncioProxyMode):
    """A regular HTTP(S) proxy that is interfaced with `HTTP CONNECT` calls (or absolute-form HTTP requests)."""
    description = "HTTP(S) proxy"
    layer = layers.modes.HttpProxy
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class TransparentMode(AsyncioProxyMode):
    """A transparent proxy, see https://docs.mitmproxy.org/dev/howto-transparent/"""
    description = "transparent proxy"
    layer = layers.modes.TransparentProxy
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class UpstreamMode(AsyncioProxyMode):
    """A regular HTTP(S) proxy, but all connections are forwarded to a second upstream HTTP(S) proxy."""
    description = "HTTP(S) proxy (upstream mode)"
    layer = layers.modes.HttpUpstreamProxy
    transport_protocol = TCP
    scheme: Literal["http", "https"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        scheme, self.address = server_spec.parse(self.data, default_scheme="http")
        if scheme != "http" and scheme != "https":
            raise ValueError("invalid upstream proxy scheme")
        self.scheme = scheme


class ReverseMode(AsyncioProxyMode):
    """A reverse proxy. This acts like a normal server, but redirects all requests to a fixed target."""
    description = "reverse proxy"
    layer = layers.modes.ReverseProxy
    transport_protocol = TCP
    scheme: Literal["http", "https", "tls", "dtls", "tcp", "udp", "dns"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        self.scheme, self.address = server_spec.parse(self.data, default_scheme="https")
        if self.scheme in ("dns", "dtls", "udp"):
            self.transport_protocol = UDP
        self.description = f"{self.description} to {self.data}"


class Socks5Mode(AsyncioProxyMode):
    """A SOCKSv5 proxy."""
    description = "SOCKS v5 proxy"
    layer = layers.modes.Socks5Proxy
    default_port = 1080
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class DnsMode(AsyncioProxyMode):
    """A DNS server."""
    description = "DNS server"
    layer = layers.DNSLayer
    default_port = 53
    transport_protocol = UDP

    def __post_init__(self) -> None:
        _check_empty(self.data)
