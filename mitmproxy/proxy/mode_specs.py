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
    data: str
    custom_listen_host: str | None
    custom_listen_port: int | None

    transport_protocol: ClassVar[Literal["tcp", "udp"]] = "tcp"
    """
    The transport protocol used by this mode. Used to detect multiple servers targeting the same proto+port.
    """
    default_port: ClassVar[int] = 8080
    __modes: ClassVar[dict[str, type[ProxyMode]]] = {}

    @abstractmethod
    def __post_init__(self) -> None:
        """Validation of data happens here."""

    def listen_host(self, default: str | None = None) -> str:
        if self.custom_listen_host is not None:
            return self.custom_listen_host
        elif default is not None:
            return default
        else:
            return ""

    def listen_port(self, default: int | None = None) -> int:
        if self.custom_listen_port is not None:
            return self.custom_listen_port
        elif default is not None:
            return default
        else:
            return self.default_port

    @classmethod
    @property
    def type(cls) -> str:
        return cls.__name__.removesuffix("Mode").lower()

    @classmethod
    @cache
    def parse(cls: Type[Self], spec: str) -> Self:
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
            mode_cls = ProxyMode.__modes[mode.lower()]
        except KeyError:
            raise ValueError(f"unknown mode")

        if not issubclass(mode_cls, cls):
            raise ValueError(f"{mode!r} is not a spec for a {cls.type} mode")

        return mode_cls(
            full_spec=spec,
            data=data,
            custom_listen_host=host,
            custom_listen_port=port
        )

    def __init_subclass__(cls, **kwargs):
        t = cls.type.lower()
        assert t not in ProxyMode.__modes
        ProxyMode.__modes[t] = cls

    @classmethod
    def from_state(cls, state):
        return ProxyMode.parse(state)

    def get_state(self):
        return self.full_spec

    def set_state(self, state):
        if state != self.full_spec:
            raise RuntimeError("Proxy modes are frozen.")


def _check_empty(data):
    if data:
        raise ValueError("mode takes no arguments")


class RegularMode(ProxyMode):
    def __post_init__(self) -> None:
        _check_empty(self.data)


class TransparentMode(ProxyMode):
    def __post_init__(self) -> None:
        _check_empty(self.data)


class UpstreamMode(ProxyMode):
    scheme: Literal["http", "https"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        scheme, self.address = server_spec.parse(self.data, default_scheme="http")
        if scheme != "http" and scheme != "https":
            raise ValueError("invalid upstream proxy scheme")
        self.scheme = scheme


class ReverseMode(ProxyMode):
    scheme: Literal["http", "https", "tcp", "tls"]
    address: tuple[str, int]

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        scheme, self.address = server_spec.parse(self.data, default_scheme="https")
        if scheme != "http" and scheme != "https" and scheme != "tcp" and scheme != "tls":
            raise ValueError("invalid reverse proxy scheme")
        self.scheme = scheme


class Socks5Mode(ProxyMode):
    default_port = 1080

    def __post_init__(self) -> None:
        _check_empty(self.data)


class DnsMode(ProxyMode):
    default_port = 53
    transport_protocol: ClassVar[Literal["tcp", "udp"]] = "udp"
    scheme: Literal["dns"]  # DoH, DoQ, ...
    address: tuple[str, int] | None = None

    # noinspection PyDataclass
    def __post_init__(self) -> None:
        if self.data in ["", "resolve-local", "transparent"]:
            return
        m, _, server = self.data.partition(":")
        if m != "reverse":
            raise ValueError("invalid dns mode")
        scheme, self.address = server_spec.parse(server, "dns")
        if scheme != "dns":
            raise ValueError("invalid dns scheme")
        self.scheme = scheme

    @property
    def resolve_local(self) -> bool:
        return self.data in ["", "resolve-local"]
