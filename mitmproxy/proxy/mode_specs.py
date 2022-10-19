"""
This module is responsible for parsing proxy mode specifications such as
`"regular"`, `"reverse:https://example.com"`, or `"socks5@1234"`. The general syntax is

    mode [: mode_configuration] [@ [listen_addr:]listen_port]

For a full example, consider `reverse:https://example.com@127.0.0.1:443`.
This would spawn a reverse proxy on port 443 bound to localhost.
The mode is `reverse`, and the mode data is `https://example.com`.
Examples:

    mode = ProxyMode.parse("regular@1234")
    assert mode.listen_port == 1234
    assert isinstance(mode, RegularMode)

    ProxyMode.parse("reverse:example.com@invalid-port")  # ValueError

    RegularMode.parse("regular")  # ok
    RegularMode.parse("socks5")  # ValueError

"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from functools import cache
from typing import ClassVar, Literal, Type, TypeVar

from mitmproxy.coretypes.serializable import Serializable
from mitmproxy.net import server_spec

# Python 3.11: Use typing.Self
Self = TypeVar("Self", bound="ProxyMode")


@dataclass(frozen=True)  # type: ignore
class ProxyMode(Serializable, metaclass=ABCMeta):
    """
    Parsed representation of a proxy mode spec. Subclassed for each specific mode,
    which then does its own data validation.
    """
    full_spec: str
    """The full proxy mode spec as entered by the user."""
    data: str
    """The (raw) mode data, i.e. the part after the mode name."""
    custom_listen_host: str | None
    """A custom listen host, if specified in the spec."""
    custom_listen_port: int | None
    """A custom listen port, if specified in the spec."""

    type_name: ClassVar[str]  # automatically derived from the class name in __init_subclass__
    """The unique name for this proxy mode, e.g. "regular" or "reverse"."""
    __types: ClassVar[dict[str, Type[ProxyMode]]] = {}

    def __init_subclass__(cls, **kwargs):
        cls.type_name = cls.__name__.removesuffix("Mode").lower()
        assert cls.type_name not in ProxyMode.__types
        ProxyMode.__types[cls.type_name] = cls

    def __repr__(self):
        return f"ProxyMode.parse({self.full_spec!r})"

    @abstractmethod
    def __post_init__(self) -> None:
        """Validation of data happens here."""

    @property
    @abstractmethod
    def description(self) -> str:
        """The mode description that will be used in server logs and UI."""

    @property
    def default_port(self) -> int:
        """
        Default listen port of servers for this mode, see `ProxyMode.listen_port()`.
        """
        return 8080

    @property
    @abstractmethod
    def transport_protocol(self) -> Literal["tcp", "udp"]:
        """The transport protocol used by this mode's server."""

    @classmethod
    @cache
    def parse(cls: Type[Self], spec: str) -> Self:
        """
        Parse a proxy mode specification and return the corresponding `ProxyMode` instance.
        """
        head, _, listen_at = spec.rpartition("@")
        if not head:
            head = listen_at
            listen_at = ""

        mode, _, data = head.partition(":")

        if listen_at:
            if ":" in listen_at:
                host, _, port_str = listen_at.rpartition(":")
            else:
                host = None
                port_str = listen_at
            try:
                port = int(port_str)
                if port < 0 or 65535 < port:
                    raise ValueError
            except ValueError:
                raise ValueError(f"invalid port: {port_str}")
        else:
            host = None
            port = None

        try:
            mode_cls = ProxyMode.__types[mode.lower()]
        except KeyError:
            raise ValueError(f"unknown mode")

        if not issubclass(mode_cls, cls):
            raise ValueError(f"{mode!r} is not a spec for a {cls.type_name} mode")

        return mode_cls(
            full_spec=spec,
            data=data,
            custom_listen_host=host,
            custom_listen_port=port
        )

    def listen_host(self, default: str | None = None) -> str:
        """
        Return the address a server for this mode should listen on. This can be either directly
        specified in the spec or taken from a user-configured global default (`options.listen_host`).
        By default, return an empty string to listen on all hosts.
        """
        if self.custom_listen_host is not None:
            return self.custom_listen_host
        elif default is not None:
            return default
        else:
            return ""

    def listen_port(self, default: int | None = None) -> int:
        """
        Return the port a server for this mode should listen on. This can be either directly
        specified in the spec, taken from a user-configured global default (`options.listen_port`),
        or from `ProxyMode.default_port`.
        """
        if self.custom_listen_port is not None:
            return self.custom_listen_port
        elif default is not None:
            return default
        else:
            return self.default_port

    @classmethod
    def from_state(cls, state):
        return ProxyMode.parse(state)

    def get_state(self):
        return self.full_spec

    def set_state(self, state):
        if state != self.full_spec:
            raise RuntimeError("Proxy modes are frozen.")


TCP: Literal['tcp', 'udp'] = "tcp"
UDP: Literal['tcp', 'udp'] = "udp"


def _check_empty(data):
    if data:
        raise ValueError("mode takes no arguments")


class RegularMode(ProxyMode):
    """A regular HTTP(S) proxy that is interfaced with `HTTP CONNECT` calls (or absolute-form HTTP requests)."""
    description = "HTTP(S) proxy"
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class TransparentMode(ProxyMode):
    """A transparent proxy, see https://docs.mitmproxy.org/dev/howto-transparent/"""
    description = "transparent proxy"
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class UpstreamMode(ProxyMode):
    """A regular HTTP(S) proxy, but all connections are forwarded to a second upstream HTTP(S) proxy."""
    description = "HTTP(S) proxy (upstream mode)"
    transport_protocol = TCP
    scheme: Literal["http", "https"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        scheme, self.address = server_spec.parse(self.data, default_scheme="http")
        if scheme != "http" and scheme != "https":
            raise ValueError("invalid upstream proxy scheme")
        self.scheme = scheme


class ReverseMode(ProxyMode):
    """A reverse proxy. This acts like a normal server, but redirects all requests to a fixed target."""
    description = "reverse proxy"
    transport_protocol = TCP
    scheme: Literal["http", "https", "tls", "dtls", "tcp", "udp", "dns"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        self.scheme, self.address = server_spec.parse(self.data, default_scheme="https")
        if self.scheme in ("dns", "dtls", "udp"):
            self.transport_protocol = UDP
        self.description = f"{self.description} to {self.data}"

    @property
    def default_port(self) -> int:
        if self.scheme == "dns":
            return 53
        return super().default_port


class Socks5Mode(ProxyMode):
    """A SOCKSv5 proxy."""
    description = "SOCKS v5 proxy"
    default_port = 1080
    transport_protocol = TCP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class DnsMode(ProxyMode):
    """A DNS server."""
    description = "DNS server"
    default_port = 53
    transport_protocol = UDP

    def __post_init__(self) -> None:
        _check_empty(self.data)


class WireGuardMode(ProxyMode):
    """Proxy Server based on WireGuard"""
    description = "WireGuard server"
    default_port = 51820
    transport_protocol = UDP

    def __post_init__(self) -> None:
        pass
