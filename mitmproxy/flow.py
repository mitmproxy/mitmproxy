import time
import typing  # noqa
import uuid

from mitmproxy import controller, connection
from mitmproxy import exceptions
from mitmproxy import stateobject
from mitmproxy import version


class Error(stateobject.StateObject):
    """
    An Error.

    This is distinct from an protocol error response (say, a HTTP code 500),
    which is represented by a normal `mitmproxy.http.Response` object. This class is
    responsible for indicating errors that fall outside of normal protocol
    communications, like interrupted connections, timeouts, or protocol errors.
    """

    msg: str
    """Message describing the error."""

    timestamp: float
    """Unix timestamp of when this error happened."""

    KILLED_MESSAGE: typing.ClassVar[str] = "Connection killed."

    def __init__(self, msg: str, timestamp: typing.Optional[float] = None) -> None:
        """Create an error. If no timestamp is passed, the current time is used."""
        self.msg = msg
        self.timestamp = timestamp or time.time()

    _stateobject_attributes = dict(
        msg=str,
        timestamp=float
    )

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg

    @classmethod
    def from_state(cls, state):
        # the default implementation assumes an empty constructor. Override
        # accordingly.
        f = cls(None)
        f.set_state(state)
        return f


class Flow(stateobject.StateObject):
    """
    Base class for network flows. A flow is a collection of objects,
    for example HTTP request/response pairs or a list of TCP messages.

    See also:
     - mitmproxy.http.HTTPFlow
     - mitmproxy.tcp.TCPFlow
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

    error: typing.Optional[Error] = None
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

    is_replay: typing.Optional[str]
    """
    This attribute indicates if this flow has been replayed in either direction.

     - a value of `request` indicates that the request has been artifically replayed by mitmproxy to the server.
     - a value of `response` indicates that the response to the client's request has been set by server replay.
    """

    def __init__(
        self,
        type: str,
        client_conn: connection.Client,
        server_conn: connection.Server,
        live: bool = None
    ) -> None:
        self.type = type
        self.id = str(uuid.uuid4())
        self.client_conn = client_conn
        self.server_conn = server_conn
        self.live = live

        self.intercepted: bool = False
        self._backup: typing.Optional[Flow] = None
        self.reply: typing.Optional[controller.Reply] = None
        self.marked: str = ""
        self.is_replay: typing.Optional[str] = None
        self.metadata: typing.Dict[str, typing.Any] = dict()
        self.comment: str = ""

    _stateobject_attributes = dict(
        id=str,
        error=Error,
        client_conn=connection.Client,
        server_conn=connection.Server,
        type=str,
        intercepted=bool,
        is_replay=str,
        marked=str,
        metadata=typing.Dict[str, typing.Any],
        comment=str,
    )

    def get_state(self):
        d = super().get_state()
        d.update(version=version.FLOW_FORMAT_VERSION)
        if self._backup and self._backup != d:
            d.update(backup=self._backup)
        return d

    def set_state(self, state):
        state = state.copy()
        state.pop("version")
        if "backup" in state:
            self._backup = state.pop("backup")
        super().set_state(state)

    @classmethod
    def from_state(cls, state):
        f = cls(None, None)
        f.set_state(state)
        return f

    def copy(self):
        """Make a copy of this flow."""
        f = super().copy()
        f.live = False
        if self.reply is not None:
            f.reply = controller.DummyReply()
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
        return (
            self.reply and
            self.reply.state in {"start", "taken"} and
            not (self.error and self.error.msg == Error.KILLED_MESSAGE)
        )

    def kill(self):
        """
        Kill this flow. The current request/response will not be forwarded to its destination.
        """
        if not self.killable:
            raise exceptions.ControlException("Flow is not killable.")
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
        self.reply.take()

    def resume(self):
        """
        Continue with the flow – called after an intercept().
        """
        if not self.intercepted:
            return
        self.intercepted = False
        # If a flow is intercepted and then duplicated, the duplicated one is not taken.
        if self.reply.state == "taken":
            self.reply.commit()

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
