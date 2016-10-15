from __future__ import absolute_import, print_function, division

import time
import copy
import uuid

from mitmproxy import stateobject
from mitmproxy.models.connections import ClientConnection
from mitmproxy.models.connections import ServerConnection

from netlib import version
from typing import Optional  # noqa


class Error(stateobject.StateObject):

    """
        An Error.

        This is distinct from an protocol error response (say, a HTTP code 500),
        which is represented by a normal HTTPResponse object. This class is
        responsible for indicating errors that fall outside of normal protocol
        communications, like interrupted connections, timeouts, protocol errors.

        Exposes the following attributes:

            msg: Message describing the error
            timestamp: Seconds since the epoch
    """

    def __init__(self, msg, timestamp=None):
        """
        @type msg: str
        @type timestamp: float
        """
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

    def copy(self):
        c = copy.copy(self)
        return c


class Flow(stateobject.StateObject):

    """
    A Flow is a collection of objects representing a single transaction.
    This class is usually subclassed for each protocol, e.g. HTTPFlow.
    """

    def __init__(self, type, client_conn, server_conn, live=None):
        self.type = type
        self.id = str(uuid.uuid4())
        self.client_conn = client_conn  # type: ClientConnection
        self.server_conn = server_conn  # type: ServerConnection
        self.live = live

        self.error = None  # type: Error
        self.intercepted = False  # type: bool
        self._backup = None  # type: Optional[Flow]
        self.reply = None
        self.marked = False  # type: bool

    _stateobject_attributes = dict(
        id=str,
        error=Error,
        client_conn=ClientConnection,
        server_conn=ServerConnection,
        type=str,
        intercepted=bool,
        marked=bool,
    )

    def get_state(self):
        d = super(Flow, self).get_state()
        d.update(version=version.IVERSION)
        if self._backup and self._backup != d:
            d.update(backup=self._backup)
        return d

    def set_state(self, state):
        state.pop("version")
        if "backup" in state:
            self._backup = state.pop("backup")
        super(Flow, self).set_state(state)

    @classmethod
    def from_state(cls, state):
        f = cls(None, None)
        f.set_state(state)
        return f

    def copy(self):
        f = copy.copy(self)

        f.id = str(uuid.uuid4())
        f.live = False
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
            return self._backup != self.get_state()
        else:
            return False

    def backup(self, force=False):
        """
            Save a backup of this Flow, which can be reverted to using a
            call to .revert().
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
        return self.reply and self.reply.state in {"handled", "taken"}

    def kill(self, master):
        """
            Kill this request.
        """
        self.error = Error("Connection killed")
        self.intercepted = False
        # reply.state should only be "handled" or "taken" here.
        # if none of this is the case, .take() will raise an exception.
        if self.reply.state != "taken":
            self.reply.take()
        self.reply.kill(force=True)
        self.reply.commit()
        master.error(self)

    def intercept(self, master):
        """
            Intercept this Flow. Processing will stop until accept_intercept is
            called.
        """
        if self.intercepted:
            return
        self.intercepted = True
        self.reply.take()
        master.handle_intercept(self)

    def accept_intercept(self, master):
        """
            Continue with the flow - called after an intercept().
        """
        if not self.intercepted:
            return
        self.intercepted = False
        self.reply.ack()
        self.reply.commit()
        master.handle_accept_intercept(self)
