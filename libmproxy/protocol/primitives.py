from .. import stateobject, utils, version
from ..proxy import ServerConnection, ClientConnection
import copy


class BackreferenceMixin(object):
    """
    If an attribute from the _backrefattr tuple is set,
    this mixin sets a reference back on the attribute object.
    Example:
        e = Error()
        f = Flow()
        f.error = e
        assert f is e.flow
    """
    _backrefattr = tuple()

    def __setattr__(self, key, value):
        super(BackreferenceMixin, self).__setattr__(key, value)
        if key in self._backrefattr and value is not None:
            setattr(value, self._backrefname, self)


class Error(stateobject.SimpleStateObject):
    """
        An Error.

        This is distinct from an HTTP error response (say, a code 500), which
        is represented by a normal Response object. This class is responsible
        for indicating errors that fall outside of normal HTTP communications,
        like interrupted connections, timeouts, protocol errors.

        Exposes the following attributes:

            flow: Flow object
            msg: Message describing the error
            timestamp: Seconds since the epoch
    """
    def __init__(self, msg, timestamp=None):
        """
        @type msg: str
        @type timestamp: float
        """
        self.flow = None  # will usually be set by the flow backref mixin
        self.msg = msg
        self.timestamp = timestamp or utils.timestamp()

    _stateobject_attributes = dict(
        msg=str,
        timestamp=float
    )

    def __str__(self):
        return self.msg

    @classmethod
    def _from_state(cls, state):
        f = cls(None)  # the default implementation assumes an empty constructor. Override accordingly.
        f._load_state(state)
        return f

    def copy(self):
        c = copy.copy(self)
        return c


class Flow(stateobject.SimpleStateObject, BackreferenceMixin):
    def __init__(self, conntype, client_conn, server_conn):
        self.conntype = conntype
        self.client_conn = client_conn
        """@type: ClientConnection"""
        self.server_conn = server_conn
        """@type: ServerConnection"""

        self.error = None
        """@type: Error"""
        self._backup = None

    _backrefattr = ("error",)
    _backrefname = "flow"

    _stateobject_attributes = dict(
        error=Error,
        client_conn=ClientConnection,
        server_conn=ServerConnection,
        conntype=str
    )

    def _get_state(self):
        d = super(Flow, self)._get_state()
        d.update(version=version.IVERSION)
        return d

    def __eq__(self, other):
        return self is other

    def copy(self):
        f = copy.copy(self)

        f.client_conn = self.client_conn.copy()
        f.server_conn = self.server_conn.copy()

        if self.error:
            f.error = self.error.copy()
        return f

    def modified(self):
        """
            Has this Flow been modified?
        """
        if self._backup:
            return self._backup != self._get_state()
        else:
            return False

    def backup(self, force=False):
        """
            Save a backup of this Flow, which can be reverted to using a
            call to .revert().
        """
        if not self._backup:
            self._backup = self._get_state()

    def revert(self):
        """
            Revert to the last backed up state.
        """
        if self._backup:
            self._load_state(self._backup)
            self._backup = None