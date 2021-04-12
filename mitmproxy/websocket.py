"""
Mitmproxy used to have its own WebSocketFlow type until mitmproxy 6, but now WebSocket connections now are represented
as HTTP flows as well. They can be distinguished from regular HTTP requests by having the
`mitmproxy.http.HTTPFlow.websocket` attribute set.

This module only defines the classes for individual `WebSocketMessage`s and the `WebSocketData` container.
"""
import time
from typing import List, Tuple, Union
from typing import Optional

from mitmproxy import stateobject
from mitmproxy.coretypes import serializable

WebSocketMessageState = Tuple[bool, bool, bytes, float, bool]


class WebSocketMessage(serializable.Serializable):
    """
    A single WebSocket message sent from one peer to the other.

    Fragmented WebSocket messages are reassembled by mitmproxy and the
    represented as a single instance of this class.

    The [WebSocket RFC](https://tools.ietf.org/html/rfc6455) specifies both
    text and binary messages. To avoid a whole class of nasty type confusion bugs,
    mitmproxy stores all message contents as binary.
    If you need text, you can use the `text` property when the message `is_text`.

    Per the WebSocket spec, text messages always use UTF-8 encoding.
    """

    from_client: bool
    """True if this messages was sent by the client."""
    is_text: bool
    """
    True if this message is a text message, False if it is binary.
    Note that mitmproxy will internally always store the message `content` as *bytes*.
    """
    content: bytes
    """A byte-string representing the content of this message."""
    timestamp: float
    """Timestamp of when this message was received or created."""
    killed: bool
    """True if the message has not been forwarded by mitmproxy, False otherwise."""

    def __init__(
        self,
        is_text: bool,
        from_client: bool,
        content: bytes,
        timestamp: Optional[float] = None,
        killed: bool = False,
    ) -> None:
        self.is_text = is_text
        self.from_client = from_client
        self.content = content
        self.timestamp: float = timestamp or time.time()
        self.killed = killed

    @classmethod
    def from_state(cls, state: WebSocketMessageState):
        return cls(*state)

    def get_state(self) -> WebSocketMessageState:
        return self.is_text, self.from_client, self.content, self.timestamp, self.killed

    def set_state(self, state: WebSocketMessageState) -> None:
        self.is_text, self.from_client, self.content, self.timestamp, self.killed = state

    def __repr__(self):
        if self.is_text:
            return repr(self.content.decode(errors="replace"))
        else:
            return repr(self.content)

    def kill(self):
        # Likely to be replaced with .drop() in the future, see https://github.com/mitmproxy/mitmproxy/pull/4486
        self.killed = True

    @property
    def text(self) -> str:
        """
        The message content as text.

        Accessing this attribute may raise a `ValueError` when the message is not a text message (Opcode.TEXT).

        *See also:* `WebSocketMessage.content`
        """
        if self.is_text:
            raise ValueError("Cannot access text property of a non-text WebSocket message")

        return self.content.decode()

    @text.setter
    def text(self, value: str) -> None:
        """
        Set the message bytes from the given string.

        Setting this attribute may raise a `ValueError` when the message is not a text message (Opcode.TEXT).

        *See also:* `WebSocketMessage.content`
        """
        if self.is_text:
            raise ValueError("Cannot set text property of a non-text WebSocket message")

        self.content = value.encode()


class WebSocketData(stateobject.StateObject):
    """
    A data container for everything related to a single WebSocket connection.
    This is typically accessed as `mitmproxy.http.HTTPFlow.websocket`.
    """

    messages: List[WebSocketMessage]
    """All `WebSocketMessage`s transferred over this connection."""

    closed_by_client: Optional[bool] = None
    """
    True if the client closed the connection,
    False if the server closed the connection,
    None if the connection is active.
    """
    close_code: Optional[int] = None
    """[Close Code](https://tools.ietf.org/html/rfc6455#section-7.1.5)"""
    close_reason: Optional[str] = None
    """[Close Reason](https://tools.ietf.org/html/rfc6455#section-7.1.6)"""

    timestamp_end: Optional[float] = None
    """*Timestamp:* WebSocket connection closed."""

    _stateobject_attributes = dict(
        messages=List[WebSocketMessage],
        closed_by_client=bool,
        close_code=int,
        close_reason=str,
        timestamp_end=float,
    )

    def __init__(self):
        self.messages = []

    def __repr__(self):
        return f"<WebSocketData ({len(self.messages)} messages)>"

    @classmethod
    def from_state(cls, state):
        d = WebSocketData()
        d.set_state(state)
        return d
