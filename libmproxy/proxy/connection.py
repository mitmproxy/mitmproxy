from __future__ import absolute_import
import copy
import os
from netlib import tcp, certutils
from .. import stateobject, utils
from .primitives import ProxyError


class ClientConnection(tcp.BaseHandler, stateobject.SimpleStateObject):
    def __init__(self, client_connection, address, server):
        if client_connection:  # Eventually, this object is restored from state. We don't have a connection then.
            tcp.BaseHandler.__init__(self, client_connection, address, server)
        else:
            self.connection = None
            self.server = None
            self.wfile = None
            self.rfile = None
            self.address = None
            self.clientcert = None

        self.timestamp_start = utils.timestamp()
        self.timestamp_end = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        timestamp_start=float,
        timestamp_end=float,
        timestamp_ssl_setup=float
    )

    def _get_state(self):
        d = super(ClientConnection, self)._get_state()
        d.update(
            address={"address": self.address(), "use_ipv6": self.address.use_ipv6},
            clientcert=self.cert.to_pem() if self.clientcert else None
        )
        return d

    def _load_state(self, state):
        super(ClientConnection, self)._load_state(state)
        self.address = tcp.Address(**state["address"]) if state["address"] else None
        self.clientcert = certutils.SSLCert.from_pem(state["clientcert"]) if state["clientcert"] else None

    def copy(self):
        return copy.copy(self)

    def send(self, message):
        self.wfile.write(message)
        self.wfile.flush()

    @classmethod
    def _from_state(cls, state):
        f = cls(None, tuple(), None)
        f._load_state(state)
        return f

    def convert_to_ssl(self, *args, **kwargs):
        tcp.BaseHandler.convert_to_ssl(self, *args, **kwargs)
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        tcp.BaseHandler.finish(self)
        self.timestamp_end = utils.timestamp()


class ServerConnection(tcp.TCPClient, stateobject.SimpleStateObject):
    def __init__(self, address, priority):
        tcp.TCPClient.__init__(self, address)
        self.priority = priority

        self.peername = None
        self.sockname = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        peername=tuple,
        sockname=tuple,
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

    def _get_state(self):
        d = super(ServerConnection, self)._get_state()
        d.update(
            address={"address": self.address(), "use_ipv6": self.address.use_ipv6},
            source_address= {"address": self.source_address(),
                             "use_ipv6": self.source_address.use_ipv6} if self.source_address else None,
            cert=self.cert.to_pem() if self.cert else None
        )
        return d

    def _load_state(self, state):
        super(ServerConnection, self)._load_state(state)

        self.address = tcp.Address(**state["address"]) if state["address"] else None
        self.source_address = tcp.Address(**state["source_address"]) if state["source_address"] else None
        self.cert = certutils.SSLCert.from_pem(state["cert"]) if state["cert"] else None

    @classmethod
    def _from_state(cls, state):
        f = cls(tuple(), None)
        f._load_state(state)
        return f

    def copy(self):
        return copy.copy(self)

    def connect(self):
        self.timestamp_start = utils.timestamp()
        tcp.TCPClient.connect(self)
        self.peername = self.connection.getpeername()
        self.sockname = self.connection.getsockname()
        self.timestamp_tcp_setup = utils.timestamp()

    def send(self, message):
        self.wfile.write(message)
        self.wfile.flush()

    def establish_ssl(self, clientcerts, sni):
        clientcert = None
        if clientcerts:
            path = os.path.join(clientcerts, self.address.host.encode("idna")) + ".pem"
            if os.path.exists(path):
                clientcert = path
        try:
            self.convert_to_ssl(cert=clientcert, sni=sni)
            self.timestamp_ssl_setup = utils.timestamp()
        except tcp.NetLibError, v:
            raise ProxyError(400, str(v))

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = utils.timestamp()