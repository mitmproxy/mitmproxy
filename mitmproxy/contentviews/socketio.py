from enum import Enum
from typing import Iterable

from mitmproxy.contentviews import base
from mitmproxy.flow import Flow


class PacketType(Enum):
    visible: bool

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
            self.BINARY_ACK
        )

BLANK = "Socket.IO", iter([])

def format_text(packet_type: PacketType, data):
    return "Socket.IO", iter([[
        ("content_none", f"{packet_type} "),
        ("text", data),
    ]])

class ViewSocketIO(base.View):
    name = "Socket.IO"

    def __call__(self, data, **metadata):
        try:
            packet_type = EngineIO(data[0])
            data = data[1:]
        except (IndexError, ValueError):
            return None

        if not packet_type.visible:
            return BLANK

        if packet_type != EngineIO.MESSAGE:
            return format_text(packet_type, data)

        try:
            packet_type = SocketIO(data[0])
            data = data[1:]
        except (IndexError, ValueError):
            return None

        if not packet_type.visible:
            return BLANK

        return format_text(packet_type, data)

    def render_priority(
        self, data: bytes, *, flow: Flow | None = None, **metadata
    ) -> float:
        return 0