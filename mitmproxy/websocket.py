import time
import queue
from typing import List, Optional

from wsproto.frame_protocol import CloseReason
from wsproto.frame_protocol import Opcode

from mitmproxy import flow
from mitmproxy.net import websockets
from mitmproxy.coretypes import serializable
from mitmproxy.utils import strutils, human


class WebSocketMessage(serializable.Serializable):
    """
    A WebSocket message sent from one endpoint to the other.
    """

    def __init__(
        self, type: int, from_client: bool, content: bytes, timestamp: Optional[int]=None, killed: bool=False
    ) -> None:
        self.type = Opcode(type)  # type: ignore
        """indicates either TEXT or BINARY (from wsproto.frame_protocol.Opcode)."""
        self.from_client = from_client
        """True if this messages was sent by the client."""
        self.content = content
        """A byte-string representing the content of this message."""
        self.timestamp: int = timestamp or int(time.time())
        """Timestamp of when this message was received or created."""
        self.killed = killed
        """True if this messages was killed and should not be sent to the other endpoint."""

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return int(self.type), self.from_client, self.content, self.timestamp, self.killed

    def set_state(self, state):
        self.type, self.from_client, self.content, self.timestamp, self.killed = state
        self.type = Opcode(self.type)  # replace enum with bare int

    def __repr__(self):
        if self.type == Opcode.TEXT:
            return "text message: {}".format(repr(self.content))
        else:
            return "binary message: {}".format(strutils.bytes_to_escaped_str(self.content))

    def kill(self):
        """
        Kill this message.

        It will not be sent to the other endpoint. This has no effect in streaming mode.
        """
        self.killed = True


class WebSocketFlow(flow.Flow):
    """
    A WebSocketFlow is a simplified representation of a Websocket connection.
    """

    def __init__(self, client_conn, server_conn, handshake_flow, live=None):
        super().__init__("websocket", client_conn, server_conn, live)

        self.messages: List[WebSocketMessage] = []
        """A list containing all WebSocketMessage's."""
        self.close_sender = 'client'
        """'client' if the client initiated connection closing."""
        self.close_code = CloseReason.NORMAL_CLOSURE
        """WebSocket close code."""
        self.close_message = '(message missing)'
        """WebSocket close message."""
        self.close_reason = 'unknown status code'
        """WebSocket close reason."""
        self.stream = False
        """True of this connection is streaming directly to the other endpoint."""
        self.handshake_flow = handshake_flow
        """The HTTP flow containing the initial WebSocket handshake."""
        self.ended = False
        """True when the WebSocket connection has been closed."""

        self._inject_messages_client = queue.Queue(maxsize=1)
        self._inject_messages_server = queue.Queue(maxsize=1)

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

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    # mypy doesn't support update with kwargs
    _stateobject_attributes.update(dict(
        messages=List[WebSocketMessage],
        close_sender=str,
        close_code=int,
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

    def get_state(self):
        d = super().get_state()
        d['close_code'] = int(d['close_code'])  # replace enum with bare int
        return d

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

    def inject_message(self, endpoint, payload):
        """
        Inject and send a full WebSocket message to the remote endpoint.
        This might corrupt your WebSocket connection! Be careful!

        The endpoint needs to be either flow.client_conn or flow.server_conn.

        If ``payload`` is of type ``bytes`` then the message is flagged as
        being binary If it is of type ``str`` encoded as UTF-8 and sent as
        text.

        :param payload: The message body to send.
        :type payload: ``bytes`` or ``str``
        """

        if endpoint == self.client_conn:
            self._inject_messages_client.put(payload)
        elif endpoint == self.server_conn:
            self._inject_messages_server.put(payload)
        else:
            raise ValueError('Invalid endpoint')
