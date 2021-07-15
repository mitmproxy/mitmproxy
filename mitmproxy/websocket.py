"""
Mitmproxy used to have its own WebSocketFlow type until mitmproxy 6, but now WebSocket connections now are represented
as HTTP flows as well. They can be distinguished from regular HTTP requests by having the
`mitmproxy.http.HTTPFlow.websocket` attribute set.

This module only defines the classes for individual `WebSocketMessage`s and the `WebSocketData` container.
"""
import time
import warnings
from typing import List, Tuple, Union
from typing import Optional

from mitmproxy import stateobject
from mitmproxy.coretypes import serializable
from wsproto.frame_protocol import Opcode

WebSocketMessageState = Tuple[int, bool, bytes, float, bool]


class WebSocketMessage(serializable.Serializable):
    """
    A single WebSocket message sent from one peer to the other.

    Fragmented WebSocket messages are reassembled by mitmproxy and then
    represented as a single instance of this class.

    The [WebSocket RFC](https://tools.ietf.org/html/rfc6455) specifies both
    text and binary messages. To avoid a whole class of nasty type confusion bugs,
    mitmproxy stores all message contents as `bytes`. If you need a `str`, you can access the `text` property
    on text messages:

    >>> if message.is_text:
    >>>     text = message.text
    """

    from_client: bool
    """True if this messages was sent by the client."""
    type: Opcode
    """
    The message type, as per RFC 6455's [opcode](https://tools.ietf.org/html/rfc6455#section-5.2).

    Mitmproxy currently only exposes messages assembled from `TEXT` and `BINARY` frames.
    """
    content: bytes
    """A byte-string representing the content of this message."""
    timestamp: float
    """Timestamp of when this message was received or created."""
    dropped: bool
    """True if the message has not been forwarded by mitmproxy, False otherwise."""

    def __init__(
        self,
        type: Union[int, Opcode],
        from_client: bool,
        content: bytes,
        timestamp: Optional[float] = None,
        killed: bool = False,
    ) -> None:
        self.from_client = from_client
        self.type = Opcode(type)
        self.content = content
        self.timestamp: float = timestamp or time.time()
        self.dropped = killed

    @classmethod
    def from_state(cls, state: WebSocketMessageState):
        return cls(*state)

    def get_state(self) -> WebSocketMessageState:
        return int(self.type), self.from_client, self.content, self.timestamp, self.dropped

    def set_state(self, state: WebSocketMessageState) -> None:
        typ, self.from_client, self.content, self.timestamp, self.dropped = state
        self.type = Opcode(typ)

    def __repr__(self):
        if self.type == Opcode.TEXT:
            return repr(self.content.decode(errors="replace"))
        else:
            return repr(self.content)

    @property
    def is_text(self) -> bool:
        """
        `True` if this message is assembled from WebSocket `TEXT` frames,
        `False` if it is assembled from `BINARY` frames.
        """
        return self.type == Opcode.TEXT

    def drop(self):
        """Drop this message, i.e. don't forward it to the other peer."""
        self.dropped = True

    def kill(self):  # pragma: no cover
        """A deprecated alias for `.drop()`."""
        warnings.warn("WebSocketMessage.kill() is deprecated, use .drop() instead.", DeprecationWarning, stacklevel=2)
        self.drop()

    @property
    def text(self) -> str:
        """
        The message content as text.

        This attribute is only available if `WebSocketMessage.is_text` is `True`.

        *See also:* `WebSocketMessage.content`
        """
        if self.type != Opcode.TEXT:
            raise AttributeError(f"{self.type.name.title()} WebSocket frames do not have a 'text' attribute.")

        return self.content.decode()

    @text.setter
    def text(self, value: str) -> None:
        if self.type != Opcode.TEXT:
            raise AttributeError(f"{self.type.name.title()} WebSocket frames do not have a 'text' attribute.")

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
    `True` if the client closed the connection,
    `False` if the server closed the connection,
    `None` if the connection is active.
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
