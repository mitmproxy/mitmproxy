import time

import os
import uuid

from mitmproxy import stateobject
from mitmproxy import certs
from mitmproxy.net import tcp
from mitmproxy.utils import strutils


class ClientConnection(tcp.BaseHandler, stateobject.StateObject):

    """
    A client connection

    Attributes:
        address: Remote address
        tls_established: True if TLS is established, False otherwise
        clientcert: The TLS client certificate
        mitmcert: The MITM'ed TLS server certificate presented to the client
        timestamp_start: Connection start timestamp
        timestamp_tls_setup: TLS established timestamp
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
            self.tls_established = None

        self.id = str(uuid.uuid4())
        self.mitmcert = None
        self.timestamp_start = time.time()
        self.timestamp_end = None
        self.timestamp_tls_setup = None
        self.sni = None
        self.cipher_name = None
        self.alpn_proto_negotiated = None
        self.tls_version = None

    def connected(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.tls_established:
            tls = "[{}] ".format(self.tls_version)
        else:
            tls = ""

        if self.alpn_proto_negotiated:
            alpn = "[ALPN: {}] ".format(
                strutils.bytes_to_escaped_str(self.alpn_proto_negotiated)
            )
        else:
            alpn = ""

        return "<ClientConnection: {tls}{alpn}{host}:{port}>".format(
            tls=tls,
            alpn=alpn,
            host=self.address[0],
            port=self.address[1],
        )

    def __eq__(self, other):
        if isinstance(other, ClientConnection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    _stateobject_attributes = dict(
        id=str,
        address=tuple,
        tls_established=bool,
        clientcert=certs.SSLCert,
        mitmcert=certs.SSLCert,
        timestamp_start=float,
        timestamp_tls_setup=float,
        timestamp_end=float,
        sni=str,
        cipher_name=str,
        alpn_proto_negotiated=bytes,
        tls_version=str,
    )

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
            id=str(uuid.uuid4()),
            address=address,
            clientcert=None,
            mitmcert=None,
            tls_established=False,
            timestamp_start=None,
            timestamp_end=None,
            timestamp_tls_setup=None,
            sni=None,
            cipher_name=None,
            alpn_proto_negotiated=None,
            tls_version=None,
        ))

    def convert_to_tls(self, cert, *args, **kwargs):
        super().convert_to_tls(cert, *args, **kwargs)
        self.timestamp_tls_setup = time.time()
        self.mitmcert = cert
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
        tls_established: True if TLS is established, False otherwise
        cert: The certificate presented by the remote during the TLS handshake
        sni: Server Name Indication sent by the proxy during the TLS handshake
        alpn_proto_negotiated: The negotiated application protocol
        tls_version: TLS version
        via: The underlying server connection (e.g. the connection to the upstream proxy in upstream proxy mode)
        timestamp_start: Connection start timestamp
        timestamp_tcp_setup: TCP ACK received timestamp
        timestamp_tls_setup: TLS established timestamp
        timestamp_end: Connection end timestamp
    """

    def __init__(self, address, source_address=None, spoof_source_address=None):
        tcp.TCPClient.__init__(self, address, source_address, spoof_source_address)

        self.id = str(uuid.uuid4())
        self.alpn_proto_negotiated = None
        self.tls_version = None
        self.via = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_tls_setup = None

    def connected(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.tls_established and self.sni:
            tls = "[{}: {}] ".format(self.tls_version or "TLS", self.sni)
        elif self.tls_established:
            tls = "[{}] ".format(self.tls_version or "TLS")
        else:
            tls = ""
        if self.alpn_proto_negotiated:
            alpn = "[ALPN: {}] ".format(
                strutils.bytes_to_escaped_str(self.alpn_proto_negotiated)
            )
        else:
            alpn = ""
        return "<ServerConnection: {tls}{alpn}{host}:{port}>".format(
            tls=tls,
            alpn=alpn,
            host=self.address[0],
            port=self.address[1],
        )

    def __eq__(self, other):
        if isinstance(other, ServerConnection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    _stateobject_attributes = dict(
        id=str,
        address=tuple,
        ip_address=tuple,
        source_address=tuple,
        tls_established=bool,
        cert=certs.SSLCert,
        sni=str,
        alpn_proto_negotiated=bytes,
        tls_version=str,
        timestamp_start=float,
        timestamp_tcp_setup=float,
        timestamp_tls_setup=float,
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
            id=str(uuid.uuid4()),
            address=address,
            ip_address=address,
            cert=None,
            sni=None,
            alpn_proto_negotiated=None,
            tls_version=None,
            source_address=('', 0),
            tls_established=False,
            timestamp_start=None,
            timestamp_tcp_setup=None,
            timestamp_tls_setup=None,
            timestamp_end=None,
            via=None
        ))

    def connect(self):
        self.timestamp_start = time.time()
        tcp.TCPClient.connect(self)
        self.timestamp_tcp_setup = time.time()

    def send(self, message):
        if isinstance(message, list):
            message = b''.join(message)
        self.wfile.write(message)
        self.wfile.flush()

    def establish_tls(self, clientcerts, sni, **kwargs):
        if sni and not isinstance(sni, str):
            raise ValueError("sni must be str, not " + type(sni).__name__)
        clientcert = None
        if clientcerts:
            if os.path.isfile(clientcerts):
                clientcert = clientcerts
            else:
                path = os.path.join(
                    clientcerts,
                    self.address[0].encode("idna").decode()) + ".pem"
                if os.path.exists(path):
                    clientcert = path

        self.convert_to_tls(cert=clientcert, sni=sni, **kwargs)
        self.sni = sni
        self.alpn_proto_negotiated = self.get_alpn_proto_negotiated()
        self.tls_version = self.connection.get_protocol_version_name()
        self.timestamp_tls_setup = time.time()

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = time.time()


ServerConnection._stateobject_attributes["via"] = ServerConnection
