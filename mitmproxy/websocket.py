import time
from typing import List, Optional

from mitmproxy import flow
from mitmproxy.net import websockets
from mitmproxy.coretypes import serializable
from mitmproxy.utils import strutils, human


class WebSocketMessage(serializable.Serializable):
    def __init__(
        self, type: int, from_client: bool, content: bytes, timestamp: Optional[int]=None
    ) -> None:
        self.type = type
        self.from_client = from_client
        self.content = content
        self.timestamp = timestamp or int(time.time())  # type: int

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.type, self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.type, self.from_client, self.content, self.timestamp = state

    def __repr__(self):
        if self.type == websockets.OPCODE.TEXT:
            return "text message: {}".format(repr(self.content))
        else:
            return "binary message: {}".format(strutils.bytes_to_escaped_str(self.content))


class WebSocketFlow(flow.Flow):
    """
    A WebsocketFlow is a simplified representation of a Websocket session.
    """

    def __init__(self, client_conn, server_conn, handshake_flow, live=None):
        super().__init__("websocket", client_conn, server_conn, live)
        self.messages = []  # type: List[WebSocketMessage]
        self.close_sender = 'client'
        self.close_code = '(status code missing)'
        self.close_message = '(message missing)'
        self.close_reason = 'unknown status code'
        self.stream = False

        if handshake_flow:
            self.client_key = websockets.get_client_key(handshake_flow.request.headers)
            self.client_protocol = websockets.get_protocol(handshake_flow.request.headers)
            self.client_extensions = websockets.get_extensions(handshake_flow.request.headers)
            self.server_accept = websockets.get_server_accept(handshake_flow.response.headers)
            self.server_protocol = websockets.get_protocol(handshake_flow.response.headers)
            self.server_extensions = websockets.get_extensions(handshake_flow.response.headers)
        else:
            self.client_key = ''
            self.client_protocol = ''
            self.client_extensions = ''
            self.server_accept = ''
            self.server_protocol = ''
            self.server_extensions = ''

        self.handshake_flow = handshake_flow

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    # mypy doesn't support update with kwargs
    _stateobject_attributes.update(dict(
        messages=List[WebSocketMessage],
        close_sender=str,
        close_code=str,
        close_message=str,
        close_reason=str,
        client_key=str,
        client_protocol=str,
        client_extensions=str,
        server_accept=str,
        server_protocol=str,
        server_extensions=str,
        # Do not include handshake_flow, to prevent recursive serialization!
        # Since mitmproxy-console currently only displays HTTPFlows,
        # dumping the handshake_flow will include the WebSocketFlow too.
    ))

    @classmethod
    def from_state(cls, state):
        f = cls(None, None, None)
        f.set_state(state)
        return f

    def __repr__(self):
        return "<WebSocketFlow ({} messages)>".format(len(self.messages))

    def message_info(self, message: WebSocketMessage) -> str:
        return "{client} {direction} WebSocket {type} message {direction} {server}{endpoint}".format(
            type=message.type,
            client=human.format_address(self.client_conn.address),
            server=human.format_address(self.server_conn.address),
            direction="->" if message.from_client else "<-",
            endpoint=self.handshake_flow.request.path,
        )
