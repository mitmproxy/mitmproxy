from __future__ import (absolute_import, print_function, division)

import copy
import os

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

    def __nonzero__(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        return "<ClientConnection: {ssl}{host}:{port}>".format(
            ssl="[ssl] " if self.ssl_established else "",
            host=self.address.host,
            port=self.address.port
        )

    @property
    def tls_established(self):
        return self.ssl_established

    _stateobject_attributes = dict(
        ssl_established=bool,
        timestamp_start=float,
        timestamp_end=float,
        timestamp_ssl_setup=float
    )

    def get_state(self, short=False):
        d = super(ClientConnection, self).get_state(short)
        d.update(
            address=({
                "address": self.address(),
                "use_ipv6": self.address.use_ipv6} if self.address else {}),
            clientcert=self.cert.to_pem() if self.clientcert else None)
        return d

    def load_state(self, state):
        super(ClientConnection, self).load_state(state)
        self.address = tcp.Address(
            **state["address"]) if state["address"] else None
        self.clientcert = certutils.SSLCert.from_pem(
            state["clientcert"]) if state["clientcert"] else None

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
        f.load_state(state)
        return f

    def convert_to_ssl(self, *args, **kwargs):
        super(ClientConnection, self).convert_to_ssl(*args, **kwargs)
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        super(ClientConnection, self).finish()
        self.timestamp_end = utils.timestamp()


class ServerConnection(tcp.TCPClient, stateobject.StateObject):
    def __init__(self, address):
        tcp.TCPClient.__init__(self, address)

        self.via = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None
        self.protocol = None

    def __nonzero__(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.ssl_established and self.sni:
            ssl = "[ssl: {0}] ".format(self.sni)
        elif self.ssl_established:
            ssl = "[ssl] "
        else:
            ssl = ""
        return "<ServerConnection: {ssl}{host}:{port}>".format(
            ssl=ssl,
            host=self.address.host,
            port=self.address.port
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
        source_address=tcp.Address,
        cert=certutils.SSLCert,
        ssl_established=bool,
        sni=str
    )
    _stateobject_long_attributes = {"cert"}

    def get_state(self, short=False):
        d = super(ServerConnection, self).get_state(short)
        d.update(
            address=({"address": self.address(),
                     "use_ipv6": self.address.use_ipv6} if self.address else {}),
            source_address=({"address": self.source_address(),
                             "use_ipv6": self.source_address.use_ipv6} if self.source_address else None),
            cert=self.cert.to_pem() if self.cert else None
        )
        return d

    def load_state(self, state):
        super(ServerConnection, self).load_state(state)

        self.address = tcp.Address(
            **state["address"]) if state["address"] else None
        self.source_address = tcp.Address(
            **state["source_address"]) if state["source_address"] else None
        self.cert = certutils.SSLCert.from_pem(
            state["cert"]) if state["cert"] else None

    @classmethod
    def from_state(cls, state):
        f = cls(tuple())
        f.load_state(state)
        return f

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
