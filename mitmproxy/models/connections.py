from __future__ import (absolute_import, print_function, division)

import copy
import os

import six

from netlib import tcp, certutils
from .. import stateobject, utils


class ClientConnection(tcp.BaseHandler, stateobject.StateObject):
    def __init__(self, client_connection, address, server):
        # Eventually, this object is restored from state. We don't have a
        # connection then.
        if client_connection:
            super(ClientConnection, self).__init__(client_connection, address, server)
        else:
            self.connection = None
            self.server = None
            self.wfile = None
            self.rfile = None
            self.address = None
            self.clientcert = None
            self.ssl_established = None

        self.timestamp_start = utils.timestamp()
        self.timestamp_end = None
        self.timestamp_ssl_setup = None
        self.protocol = None

    def __bool__(self):
        return bool(self.connection) and not self.finished

    if six.PY2:
        __nonzero__ = __bool__

    def __repr__(self):
        return "<ClientConnection: {ssl}{address}>".format(
            ssl="[ssl] " if self.ssl_established else "",
            address=repr(self.address)
        )

    @property
    def tls_established(self):
        return self.ssl_established

    _stateobject_attributes = dict(
        address=tcp.Address,
        clientcert=certutils.SSLCert,
        ssl_established=bool,
        timestamp_start=float,
        timestamp_end=float,
        timestamp_ssl_setup=float
    )

    def copy(self):
        return copy.copy(self)

    def send(self, message):
        if isinstance(message, list):
            message = b''.join(message)
        self.wfile.write(message)
        self.wfile.flush()

    @classmethod
    def from_state(cls, state):
        f = cls(None, tuple(), None)
        f.set_state(state)
        return f

    @classmethod
    def make_dummy(cls, address):
        return cls.from_state(dict(
            address=dict(address=address, use_ipv6=False),
            clientcert=None,
            ssl_established=False,
            timestamp_start=None,
            timestamp_end=None,
            timestamp_ssl_setup=None
        ))

    def convert_to_ssl(self, *args, **kwargs):
        super(ClientConnection, self).convert_to_ssl(*args, **kwargs)
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        super(ClientConnection, self).finish()
        self.timestamp_end = utils.timestamp()


class ServerConnection(tcp.TCPClient, stateobject.StateObject):
    def __init__(self, address, source_address=None):
        tcp.TCPClient.__init__(self, address, source_address)

        self.via = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None
        self.protocol = None

    def __bool__(self):
        return bool(self.connection) and not self.finished

    if six.PY2:
        __nonzero__ = __bool__

    def __repr__(self):
        if self.ssl_established and self.sni:
            ssl = "[ssl: {0}] ".format(self.sni)
        elif self.ssl_established:
            ssl = "[ssl] "
        else:
            ssl = ""
        return "<ServerConnection: {ssl}{address}>".format(
            ssl=ssl,
            address=repr(self.address)
        )

    @property
    def tls_established(self):
        return self.ssl_established

    _stateobject_attributes = dict(
        timestamp_start=float,
        timestamp_end=float,
        timestamp_tcp_setup=float,
        timestamp_ssl_setup=float,
        address=tcp.Address,
        peer_address=tcp.Address,
        source_address=tcp.Address,
        cert=certutils.SSLCert,
        ssl_established=bool,
        sni=str
    )

    @classmethod
    def from_state(cls, state):
        f = cls(tuple())
        f.set_state(state)
        return f

    @classmethod
    def make_dummy(cls, address):
        return cls.from_state(dict(
            address=dict(address=address, use_ipv6=False),
            cert=None,
            sni=None,
            source_address=dict(address=('', 0), use_ipv6=False),
            ssl_established=False,
            timestamp_start=None,
            timestamp_tcp_setup=None,
            timestamp_ssl_setup=None,
            timestamp_end=None,
            via=None
    ))

    def copy(self):
        return copy.copy(self)

    def connect(self):
        self.timestamp_start = utils.timestamp()
        tcp.TCPClient.connect(self)
        self.timestamp_tcp_setup = utils.timestamp()

    def send(self, message):
        if isinstance(message, list):
            message = b''.join(message)
        self.wfile.write(message)
        self.wfile.flush()

    def establish_ssl(self, clientcerts, sni, **kwargs):
        clientcert = None
        if clientcerts:
            if os.path.isfile(clientcerts):
                clientcert = clientcerts
            else:
                path = os.path.join(
                    clientcerts,
                    self.address.host.encode("idna")) + ".pem"
                if os.path.exists(path):
                    clientcert = path

        self.convert_to_ssl(cert=clientcert, sni=sni, **kwargs)
        self.sni = sni
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = utils.timestamp()


ServerConnection._stateobject_attributes["via"] = ServerConnection
