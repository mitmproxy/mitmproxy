import time
from typing import List, Optional

from mitmproxy import flow
from mitmproxy.http import HTTPFlow
from mitmproxy.net import websockets
from mitmproxy.types import serializable
from mitmproxy.utils import strutils


class WebSocketMessage(serializable.Serializable):
    def __init__(self, type: int, from_client: bool, content: bytes, timestamp: Optional[int]=None):
        self.type = type
        self.from_client = from_client
        self.content = content
        self.timestamp = timestamp or time.time()  # type: int

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
        self.handshake_flow = handshake_flow

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        messages=List[WebSocketMessage],
        close_sender=str,
        close_code=str,
        close_message=str,
        close_reason=str,
        handshake_flow=HTTPFlow,
    )

    @classmethod
    def from_state(cls, state):
        f = cls(None, None, None)
        f.set_state(state)
        return f

    def __repr__(self):
        return "<WebSocketFlow ({} messages)>".format(len(self.messages))

    @property
    def client_key(self):
        return websockets.get_client_key(self.handshake_flow.request.headers)

    @property
    def client_protocol(self):
        return websockets.get_protocol(self.handshake_flow.request.headers)

    @property
    def client_extensions(self):
        return websockets.get_extensions(self.handshake_flow.request.headers)

    @property
    def server_accept(self):
        return websockets.get_server_accept(self.handshake_flow.response.headers)

    @property
    def server_protocol(self):
        return websockets.get_protocol(self.handshake_flow.response.headers)

    @property
    def server_extensions(self):
        return websockets.get_extensions(self.handshake_flow.response.headers)

    def message_info(self, message: WebSocketMessage) -> str:
        return "{client} {direction} WebSocket {type} message {direction} {server}{endpoint}".format(
            type=message.type,
            client=repr(self.client_conn.address),
            server=repr(self.server_conn.address),
            direction="->" if message.from_client else "<-",
            endpoint=self.handshake_flow.request.path,
        )
