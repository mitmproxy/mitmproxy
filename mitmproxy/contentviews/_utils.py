from pathlib import Path

from .. import http, ctx
from ..flow import Flow
from ..tcp import TCPMessage
from ..udp import UDPMessage
from ..websocket import WebSocketMessage
from ._api import Metadata


def make_metadata(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: Flow,
) -> Metadata:
    metadata = Metadata(
        flow=flow,
        protobuf_definitions=Path(ctx.options.protobuf_definitions),
    )

    match message:
        case http.Message():
            metadata.http_message = message
            if ctype := message.headers.get("content-type"):
                if ct := http.parse_content_type(ctype):
                    metadata.content_type = f"{ct[0]}/{ct[1]}"
        case TCPMessage():
            metadata.tcp_message = message
        case UDPMessage():
            metadata.udp_message = message
        case WebSocketMessage():
            metadata.websocket_message = message

    return metadata


def get_data(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
) -> tuple[bytes | None, str]:
    content: bytes | None
    try:
        content = message.content
    except ValueError:
        assert isinstance(message, http.Message)
        content = message.raw_content
        enc = "[cannot decode]"
    else:
        if isinstance(message, http.Message) and content != message.raw_content:
            enc = "[decoded {}]".format(message.headers.get("content-encoding"))
        else:
            enc = ""

    return content, enc
