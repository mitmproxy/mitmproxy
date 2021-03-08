"""
Mitmproxy used to have its own WebSocketFlow type until mitmproxy 6, but now WebSocket connections now are represented
as HTTP flows as well. They can be distinguished from regular HTTP requests by having the
`mitmproxy.http.HTTPFlow.websocket` attribute set.

This module only defines the classes for individual `WebSocketMessage`s and the `WebSocketData` container.
"""
import time
import warnings
from typing import List
from typing import Optional

from mitmproxy import stateobject
from mitmproxy.coretypes import serializable


class WebSocketMessage(serializable.Serializable):
    """
    A single WebSocket message sent from one peer to the other.

    Fragmented WebSocket messages are reassembled by mitmproxy and the
    represented as a single instance of this class.

    The [WebSocket RFC](https://tools.ietf.org/html/rfc6455) specifies both
    text and binary messages. To avoid a whole class of nasty type confusion bugs,
    mitmproxy stores all message contents as binary. If you need text, you can decode the `content` property:

    >>> if message.is_text:
    >>>     text = message.content.decode()
    """

    from_client: bool
    """True if this messages was sent by the client."""
    is_text: bool
    """
    True if the message is a text message, False if the message is a binary message.
    
    In either case, mitmproxy will store the message contents as *bytes*.
    """
    content: bytes
    """A byte-string representing the content of this message."""
    timestamp: float
    """Timestamp of when this message was received or created."""

    def __init__(
        self,
        from_client: bool,
        is_text: bool,
        content: bytes,
        timestamp: Optional[float] = None,
    ) -> None:
        self.from_client = from_client
        self.is_text = is_text
        self.content = content
        self.timestamp: float = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.is_text, self.content, self.timestamp

    def set_state(self, state):
        self.from_client, self.is_text, self.content, self.timestamp = state

    def __repr__(self):
        if self.is_text:
            return repr(self.content.decode(errors="replace"))
        else:
            return repr(self.content)

    def kill(self):  # pragma: no cover
        """
        Kill this message.

        It will not be sent to the other endpoint.
        """
        warnings.warn(
            "WebSocketMessage.kill is deprecated, set an empty content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.content = b""

    @property
    def killed(self) -> bool:  # pragma: no cover
        """
        True if this messages was killed and should not be sent to the other endpoint.
        """
        warnings.warn(
            "WebSocketMessage.killed is deprecated, check for an empty content instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return bool(self.content)


class WebSocketData(stateobject.StateObject):
    """
    A data container for everything related to a single WebSocket connection.
    This is typically accessed as `mitmproxy.http.HTTPFlow.websocket`.
    """

    messages: List[WebSocketMessage]
    """All `WebSocketMessage`s transferred over this connection."""

    close_by_client: Optional[bool] = None
    """
    True if the client closed the connection, 
    False if the server closed the connection, 
    None if the connection is active.
    """
    close_code: Optional[int] = None
    """[Close Code](https://tools.ietf.org/html/rfc6455#section-7.1.5)"""
    close_reason: Optional[str] = None
    """[Close Reason](https://tools.ietf.org/html/rfc6455#section-7.1.6)"""

    _stateobject_attributes = dict(
        messages=List[WebSocketMessage],
        close_by_client=bool,
        close_code=int,
        close_reason=str,
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
