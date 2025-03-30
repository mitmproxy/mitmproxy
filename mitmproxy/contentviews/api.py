from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal
from mitmproxy import http, tcp, udp
from mitmproxy.flow import Flow
from mitmproxy.websocket import WebSocketMessage


class Contentview(ABC):
    """A contentview that prettifies raw data."""

    @property
    def name(self) -> str:
        """
        The name of this contentview, e.g. "XML/HTML". 
        Inferred from the class name by default.
        """
        return type(self).__name__.removesuffix("Contentview")
    
    @abstractmethod
    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        """Transform raw data into human-readable output."""

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float | None:
        """
        Return the priority of this view for rendering `data`.
        If no particular view is chosen by the user, the view with the highest priority is selected.
        If this view does not support the given data, return a float < 0.
        """

    @property
    def syntax_highlight(self) -> Literal["yaml", "none"]:
        """Optional syntax highlighting that should be applied to the prettified output."""
        return "none"

    def __lt__(self, other):
        assert isinstance(other, Contentview)
        return self.name.__lt__(other.name)


class InteractiveContentview(Contentview, metaclass=ABCMeta):
    """A contentview that prettifies raw data and allows for interactive editing."""

    @abstractmethod
    def reencode(
        self,
        prettified: str,
        metadata: Metadata,
    ) -> bytes:
        """
        Reencode the given (modified) `prettified` output into the original data format.
        """
    
@dataclass
class Metadata:
    """
    Metadata about the data that is being prettified.

    Implementations must not rely on any given attribute to be present.
    """
    flow: Flow | None = None
    """The flow that the data belongs to, if any."""

    content_type: str | None = None
    """The HTTP content type of the data, if any."""
    http_message: http.Message | None = None
    """The HTTP message that the data belongs to, if any."""
    tcp_message: tcp.TCPMessage | None = None
    """The TCP message that the data belongs to, if any."""
    udp_message: udp.UDPMessage | None = None
    """The UDP message that the data belongs to, if any."""
    websocket_message: WebSocketMessage | None = None
    """The websocket message that the data belongs to, if any."""

    original_data: bytes | None = None
    """When reencoding: The original data that was prettified."""


Metadata.__init__.__doc__ = "@private"