import time

import copy
import os

from mitmproxy import stateobject
from mitmproxy import certs
from mitmproxy.net import tcp
from mitmproxy.utils import strutils


class ClientConnection(tcp.BaseHandler, stateobject.StateObject):

    """
    A client connection

    Attributes:
        address: Remote address
        ssl_established: True if TLS is established, False otherwise
        clientcert: The TLS client certificate
        timestamp_start: Connection start timestamp
        timestamp_ssl_setup: TLS established timestamp
        timestamp_end: Connection end timestamp
        sni: Server Name Indication sent by client during the TLS handshake
        cipher_name: The current used cipher
        alpn_proto_negotiated: The negotiated application protocol
        tls_version: TLS version
    """

    def __init__(self, client_connection, address, server):
        # Eventually, this object is restored from state. We don't have a
        # connection then.
        if client_connection:
            super().__init__(client_connection, address, server)
        else:
            self.connection = None
            self.server = None
            self.wfile = None
            self.rfile = None
            self.address = None
            self.clientcert = None
            self.ssl_established = None

        self.timestamp_start = time.time()
        self.timestamp_end = None
        self.timestamp_ssl_setup = None
        self.sni = None
        self.cipher_name = None
        self.alpn_proto_negotiated = None
        self.tls_version = None

    def connected(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.alpn_proto_negotiated:
            alpn = "[ALPN: {}] ".format(
                strutils.bytes_to_escaped_str(self.alpn_proto_negotiated)
            )
        else:
            alpn = ""
        return "<ClientConnection: {ssl}{alpn}{address}>".format(
            ssl="[ssl] " if self.ssl_established else "",
            alpn=alpn,
            address=repr(self.address)
        )

    @property
    def tls_established(self):
        return self.ssl_established

    _stateobject_attributes = dict(
        address=tcp.Address,
        ssl_established=bool,
        clientcert=certs.SSLCert,
        timestamp_start=float,
        timestamp_ssl_setup=float,
        timestamp_end=float,
        sni=str,
        cipher_name=str,
        alpn_proto_negotiated=bytes,
        tls_version=str,
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
            timestamp_ssl_setup=None,
            sni=None,
            cipher_name=None,
            alpn_proto_negotiated=None,
            tls_version=None,
        ))

    def convert_to_ssl(self, *args, **kwargs):
        super().convert_to_ssl(*args, **kwargs)
        self.timestamp_ssl_setup = time.time()
        sni = self.connection.get_servername()
        if sni:
            self.sni = sni.decode("idna")
        else:
            self.sni = None
        self.cipher_name = self.connection.get_cipher_name()
        self.alpn_proto_negotiated = self.get_alpn_proto_negotiated()
        self.tls_version = self.connection.get_protocol_version_name()

    def finish(self):
        super().finish()
        self.timestamp_end = time.time()


class ServerConnection(tcp.TCPClient, stateobject.StateObject):

    """
    A server connection

    Attributes:
        address: Remote address. Can be both a domain or an IP address.
        ip_address: Resolved remote IP address.
        source_address: Local IP address or client's source IP address.
        ssl_established: True if TLS is established, False otherwise
        cert: The certificate presented by the remote during the TLS handshake
        sni: Server Name Indication sent by the proxy during the TLS handshake
        alpn_proto_negotiated: The negotiated application protocol
        via: The underlying server connection (e.g. the connection to the upstream proxy in upstream proxy mode)
        timestamp_start: Connection start timestamp
        timestamp_tcp_setup: TCP ACK received timestamp
        timestamp_ssl_setup: TLS established timestamp
        timestamp_end: Connection end timestamp
    """

    def __init__(self, address, source_address=None, spoof_source_address=None):
        tcp.TCPClient.__init__(self, address, source_address, spoof_source_address)

        self.alpn_proto_negotiated = None
        self.via = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None

    def connected(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.ssl_established and self.sni:
            ssl = "[ssl: {0}] ".format(self.sni)
        elif self.ssl_established:
            ssl = "[ssl] "
        else:
            ssl = ""
        if self.alpn_proto_negotiated:
            alpn = "[ALPN: {}] ".format(
                strutils.bytes_to_escaped_str(self.alpn_proto_negotiated)
            )
        else:
            alpn = ""
        return "<ServerConnection: {ssl}{alpn}{address}>".format(
            ssl=ssl,
            alpn=alpn,
            address=repr(self.address)
        )

    @property
    def tls_established(self):
        return self.ssl_established

    _stateobject_attributes = dict(
        address=tcp.Address,
        ip_address=tcp.Address,
        source_address=tcp.Address,
        ssl_established=bool,
        cert=certs.SSLCert,
        sni=str,
        alpn_proto_negotiated=bytes,
        timestamp_start=float,
        timestamp_tcp_setup=float,
        timestamp_ssl_setup=float,
        timestamp_end=float,
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
            ip_address=dict(address=address, use_ipv6=False),
            cert=None,
            sni=None,
            alpn_proto_negotiated=None,
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
        self.timestamp_start = time.time()
        tcp.TCPClient.connect(self)
        self.timestamp_tcp_setup = time.time()

    def send(self, message):
        if isinstance(message, list):
            message = b''.join(message)
        self.wfile.write(message)
        self.wfile.flush()

    def establish_ssl(self, clientcerts, sni, **kwargs):
        if sni and not isinstance(sni, str):
            raise ValueError("sni must be str, not " + type(sni).__name__)
        clientcert = None
        if clientcerts:
            if os.path.isfile(clientcerts):
                clientcert = clientcerts
            else:
                path = os.path.join(
                    clientcerts,
                    self.address.host.encode("idna").decode()) + ".pem"
                if os.path.exists(path):
                    clientcert = path

        self.convert_to_ssl(cert=clientcert, sni=sni, **kwargs)
        self.sni = sni
        self.alpn_proto_negotiated = self.get_alpn_proto_negotiated()
        self.timestamp_ssl_setup = time.time()

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = time.time()


ServerConnection._stateobject_attributes["via"] = ServerConnection
