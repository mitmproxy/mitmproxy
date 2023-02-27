from __future__ import annotations

import asyncio
import copy
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import ClassVar

from mitmproxy import connection
from mitmproxy import exceptions
from mitmproxy import version
from mitmproxy.coretypes import serializable


@dataclass
class Error(serializable.SerializableDataclass):
    """
    An Error.

    This is distinct from an protocol error response (say, a HTTP code 500),
    which is represented by a normal `mitmproxy.http.Response` object. This class is
    responsible for indicating errors that fall outside of normal protocol
    communications, like interrupted connections, timeouts, or protocol errors.
    """

    msg: str
    """Message describing the error."""

    timestamp: float = field(default_factory=time.time)
    """Unix timestamp of when this error happened."""

    KILLED_MESSAGE: ClassVar[str] = "Connection killed."

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg


class Flow(serializable.Serializable):
    """
    Base class for network flows. A flow is a collection of objects,
    for example HTTP request/response pairs or a list of TCP messages.

    See also:
     - mitmproxy.http.HTTPFlow
     - mitmproxy.tcp.TCPFlow
     - mitmproxy.udp.UDPFlow
    """

    client_conn: connection.Client
    """The client that connected to mitmproxy."""

    server_conn: connection.Server
    """
    The server mitmproxy connected to.

    Some flows may never cause mitmproxy to initiate a server connection,
    for example because their response is replayed by mitmproxy itself.
    To simplify implementation, those flows will still have a `server_conn` attribute
    with a `timestamp_start` set to `None`.
    """

    error: Error | None = None
    """A connection or protocol error affecting this flow."""

    intercepted: bool
    """
    If `True`, the flow is currently paused by mitmproxy.
    We're waiting for a user action to forward the flow to its destination.
    """

    marked: str = ""
    """
    If this attribute is a non-empty string the flow has been marked by the user.

    A string value will be used as the marker annotation. May either be a single character or a Unicode emoji name.

    For example `:grapes:` becomes `🍇` in views that support emoji rendering.
    Consult the [Github API Emoji List](https://api.github.com/emojis) for a list of emoji that may be used.
    Not all emoji, especially [emoji modifiers](https://en.wikipedia.org/wiki/Miscellaneous_Symbols_and_Pictographs#Emoji_modifiers)
    will render consistently.

    The default marker for the view will be used if the Unicode emoji name can not be interpreted.
    """

    is_replay: str | None
    """
    This attribute indicates if this flow has been replayed in either direction.

     - a value of `request` indicates that the request has been artifically replayed by mitmproxy to the server.
     - a value of `response` indicates that the response to the client's request has been set by server replay.
    """

    live: bool
    """
    If `True`, the flow belongs to a currently active connection.
    If `False`, the flow may have been already completed or loaded from disk.
    """

    timestamp_created: float
    """
    The Unix timestamp of when this flow was created.

    In contrast to `timestamp_start`, this value will not change when a flow is replayed.
    """

    def __init__(
        self,
        client_conn: connection.Client,
        server_conn: connection.Server,
        live: bool = False,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.client_conn = client_conn
        self.server_conn = server_conn
        self.live = live
        self.timestamp_created = time.time()

        self.intercepted: bool = False
        self._resume_event: asyncio.Event | None = None
        self._backup: Flow | None = None
        self.marked: str = ""
        self.is_replay: str | None = None
        self.metadata: dict[str, Any] = dict()
        self.comment: str = ""

    __types: dict[str, type[Flow]] = {}

    type: ClassVar[
        str
    ]  # automatically derived from the class name in __init_subclass__
    """The flow type, for example `http`, `tcp`, or `dns`."""

    def __init_subclass__(cls, **kwargs):
        cls.type = cls.__name__.removesuffix("Flow").lower()
        Flow.__types[cls.type] = cls

    def get_state(self) -> serializable.State:
        state = {
            "version": version.FLOW_FORMAT_VERSION,
            "type": self.type,
            "id": self.id,
            "error": self.error.get_state() if self.error else None,
            "client_conn": self.client_conn.get_state(),
            "server_conn": self.server_conn.get_state(),
            "intercepted": self.intercepted,
            "is_replay": self.is_replay,
            "marked": self.marked,
            "metadata": copy.deepcopy(self.metadata),
            "comment": self.comment,
            "timestamp_created": self.timestamp_created,
        }
        state["backup"] = copy.deepcopy(self._backup) if self._backup != state else None
        return state

    def set_state(self, state: serializable.State) -> None:
        assert state.pop("version") == version.FLOW_FORMAT_VERSION
        assert state.pop("type") == self.type
        self.id = state.pop("id")
        if state["error"]:
            if self.error:
                self.error.set_state(state.pop("error"))
            else:
                self.error = Error.from_state(state.pop("error"))
        else:
            self.error = state.pop("error")
        self.client_conn.set_state(state.pop("client_conn"))
        self.server_conn.set_state(state.pop("server_conn"))
        self.intercepted = state.pop("intercepted")
        self.is_replay = state.pop("is_replay")
        self.marked = state.pop("marked")
        self.metadata = state.pop("metadata")
        self.comment = state.pop("comment")
        self.timestamp_created = state.pop("timestamp_created")
        self._backup = state.pop("backup", None)
        assert state == {}

    @classmethod
    def from_state(cls, state: serializable.State) -> Flow:
        try:
            flow_cls = Flow.__types[state["type"]]
        except KeyError:
            raise ValueError(f"Unknown flow type: {state['type']}")
        client = connection.Client(peername=("", 0), sockname=("", 0))
        server = connection.Server(address=None)
        f = flow_cls(client, server)
        f.set_state(state)
        return f

    def copy(self):
        """Make a copy of this flow."""
        f = super().copy()
        f.live = False
        return f

    def modified(self):
        """
        `True` if this file has been modified by a user, `False` otherwise.
        """
        if self._backup:
            return self._backup != self.get_state()
        else:
            return False

    def backup(self, force=False):
        """
        Save a backup of this flow, which can be restored by calling `Flow.revert()`.
        """
        if not self._backup:
            self._backup = self.get_state()

    def revert(self):
        """
        Revert to the last backed up state.
        """
        if self._backup:
            self.set_state(self._backup)
            self._backup = None

    @property
    def killable(self):
        """*Read-only:* `True` if this flow can be killed, `False` otherwise."""
        return self.live and not (self.error and self.error.msg == Error.KILLED_MESSAGE)

    def kill(self):
        """
        Kill this flow. The current request/response will not be forwarded to its destination.
        """
        if not self.killable:
            raise exceptions.ControlException("Flow is not killable.")
        # TODO: The way we currently signal killing is not ideal. One major problem is that we cannot kill
        #  flows in transit (https://github.com/mitmproxy/mitmproxy/issues/4711), even though they are advertised
        #  as killable. An alternative approach would be to introduce a `KillInjected` event similar to
        #  `MessageInjected`, which should fix this issue.
        self.error = Error(Error.KILLED_MESSAGE)
        self.intercepted = False
        self.live = False

    def intercept(self):
        """
        Intercept this Flow. Processing will stop until resume is
        called.
        """
        if self.intercepted:
            return
        self.intercepted = True
        if self._resume_event is not None:
            self._resume_event.clear()

    async def wait_for_resume(self):
        """
        Wait until this Flow is resumed.
        """
        if not self.intercepted:
            return
        if self._resume_event is None:
            self._resume_event = asyncio.Event()
        await self._resume_event.wait()

    def resume(self):
        """
        Continue with the flow – called after an intercept().
        """
        if not self.intercepted:
            return
        self.intercepted = False
        if self._resume_event is not None:
            self._resume_event.set()

    @property
    def timestamp_start(self) -> float:
        """
        *Read-only:* Start time of the flow.
        Depending on the flow type, this property is an alias for
        `mitmproxy.connection.Client.timestamp_start` or `mitmproxy.http.Request.timestamp_start`.
        """
        return self.client_conn.timestamp_start


__all__ = [
    "Flow",
    "Error",
]
