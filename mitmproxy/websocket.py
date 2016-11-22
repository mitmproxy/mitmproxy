import time

from typing import List

from mitmproxy import flow
from mitmproxy.http import HTTPFlow
from mitmproxy.net import websockets
from mitmproxy.utils import strutils
from mitmproxy.types import serializable


class WebSocketMessage(serializable.Serializable):

    def __init__(self, flow, from_client, content, timestamp=None):
        self.flow = flow
        self.content = content
        self.from_client = from_client
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client = state.pop("from_client")
        self.content = state.pop("content")
        self.timestamp = state.pop("timestamp")

    @property
    def info(self):
        return "{client} {direction} WebSocket {type} message {direction} {server}{endpoint}".format(
            type=self.type,
            client=repr(self.flow.client_conn.address),
            server=repr(self.flow.server_conn.address),
            direction="->" if self.from_client else "<-",
            endpoint=self.flow.handshake_flow.request.path,
        )


class WebSocketBinaryMessage(WebSocketMessage):

    type = 'binary'

    def __repr__(self):
        return "binary message: {}".format(strutils.bytes_to_escaped_str(self.content))


class WebSocketTextMessage(WebSocketMessage):

    type = 'text'

    def __repr__(self):
        return "text message: {}".format(repr(self.content))


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
        self.client_key = websockets.get_client_key(self.handshake_flow.request.headers)
        self.client_protocol = websockets.get_protocol(self.handshake_flow.request.headers)
        self.client_extensions = websockets.get_extensions(self.handshake_flow.request.headers)
        self.server_accept = websockets.get_server_accept(self.handshake_flow.response.headers)
        self.server_protocol = websockets.get_protocol(self.handshake_flow.response.headers)
        self.server_extensions = websockets.get_extensions(self.handshake_flow.response.headers)

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        messages=List[WebSocketMessage],
        handshake_flow=HTTPFlow,
    )

    def __repr__(self):
        return "WebSocketFlow ({} messages)".format(len(self.messages))
