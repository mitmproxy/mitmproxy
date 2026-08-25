from abc import abstractmethod
from enum import Enum

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.http import HTTPFlow
from mitmproxy.utils import strutils


class PacketType(Enum):
    @property
    @abstractmethod
    def visible(self) -> bool:
        raise RuntimeError  # pragma: no cover

    def __str__(self):
        return f"{type(self).__name__}.{self.name}"


class EngineIO(PacketType):
    # https://github.com/socketio/engine.io-protocol?tab=readme-ov-file#protocol
    OPEN = ord("0")
    CLOSE = ord("1")
    PING = ord("2")
    PONG = ord("3")
    MESSAGE = ord("4")
    UPGRADE = ord("5")
    NOOP = ord("6")

    @property
    def visible(self):
        return self not in (
            self.PING,
            self.PONG,
        )


class SocketIO(PacketType):
    # https://github.com/socketio/socket.io-protocol?tab=readme-ov-file#exchange-protocol
    CONNECT = ord("0")
    DISCONNECT = ord("1")
    EVENT = ord("2")
    ACK = ord("3")
    CONNECT_ERROR = ord("4")
    BINARY_EVENT = ord("5")
    BINARY_ACK = ord("6")

    @property
    def visible(self):
        return self not in (
            self.ACK,
            self.BINARY_ACK,
        )


def parse_packet(data: bytes) -> tuple[PacketType, bytes]:
    # throws IndexError/ValueError if invalid packet
    engineio_type = EngineIO(data[0])
    data = data[1:]

    if engineio_type is not EngineIO.MESSAGE:
        return engineio_type, data

    socketio_type = SocketIO(data[0])
    data = data[1:]

    return socketio_type, data


class SocketIOContentview(Contentview):
    name = "Socket.IO"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        packet_type, msg = parse_packet(data)
        if not packet_type.visible:
            return ""
        return f"{packet_type} {strutils.bytes_to_escaped_str(msg)}"

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(
            bool(
                data
                and isinstance(metadata.flow, HTTPFlow)
                and metadata.flow.websocket is not None
                and "/socket.io/?" in metadata.flow.request.path
            )
        )


socket_io = SocketIOContentview()
