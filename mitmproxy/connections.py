import os
import time
import typing
import uuid
import warnings

from mitmproxy import certs
from mitmproxy import exceptions
from mitmproxy import stateobject
from mitmproxy.net import tcp
from mitmproxy.net import tls
from mitmproxy.utils import human
from mitmproxy.utils import strutils


class ClientConnection(tcp.BaseHandler, stateobject.StateObject):
    """
    A client connection

    Attributes:
        address: Remote address
        tls_established: True if TLS is established, False otherwise
        mitmcert: The MITM'ed TLS server certificate presented to the client
        timestamp_start: Connection start timestamp
        timestamp_tls_setup: TLS established timestamp
        timestamp_end: Connection end timestamp
        sni: Server Name Indication sent by client during the TLS handshake
        cipher_name: The current used cipher
        alpn_proto_negotiated: The negotiated application protocol
        tls_version: TLS version
        tls_extensions: TLS ClientHello extensions
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
        self.tls_extensions = None

    def connected(self):
        return bool(self.connection) and not self.finished

    def __repr__(self):
        if self.tls_established:
            tls = f"[{self.tls_version}] "
        else:
            tls = ""

        if self.alpn_proto_negotiated:
            alpn = "[ALPN: {}] ".format(
                strutils.bytes_to_escaped_str(self.alpn_proto_negotiated)
            )
        else:
            alpn = ""

        return "<ClientConnection: {tls}{alpn}{address}>".format(
            tls=tls,
            alpn=alpn,
            address=human.format_address(self.address),
        )

    def __eq__(self, other):
        if isinstance(other, ClientConnection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    # Sans-io attributes.
    state = 0
    sockname = ("", 0)
    error = None
    tls = None
    certificate_list = ()
    alpn_offers = None
    cipher_list = None

    _stateobject_attributes = dict(
        id=str,
        address=tuple,
        tls_established=bool,
        mitmcert=certs.Cert,
        timestamp_start=float,
        timestamp_tls_setup=float,
        timestamp_end=float,
        sni=str,
        cipher_name=str,
        alpn_proto_negotiated=bytes,
        tls_version=str,
        tls_extensions=typing.List[typing.Tuple[int, bytes]],
        # sans-io exclusives
        state=int,
        sockname=tuple,
        error=str,
        tls=bool,
        certificate_list=typing.List[certs.Cert],
        alpn_offers=typing.List[bytes],
        cipher_list=typing.List[str],
    )

    @property
    def clientcert(self) -> typing.Optional[certs.Cert]:  # pragma: no cover
        warnings.warn(".clientcert is deprecated, use .certificate_list instead.", PendingDeprecationWarning)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @clientcert.setter
    def clientcert(self, val):  # pragma: no cover
        warnings.warn(".clientcert is deprecated, use .certificate_list instead.", PendingDeprecationWarning)
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []

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
            mitmcert=None,
            tls_established=False,
            timestamp_start=None,
            timestamp_end=None,
            timestamp_tls_setup=None,
            sni=None,
            cipher_name=None,
            alpn_proto_negotiated=None,
            tls_version=None,
            tls_extensions=None,
            state=0,
            sockname=("", 0),
            error=None,
            tls=False,
            certificate_list=[],
            alpn_offers=[],
            cipher_list=[],
        ))

    def convert_to_tls(self, cert, *args, **kwargs):
        # Unfortunately OpenSSL provides no way to expose all TLS extensions, so we do this dance
        # here and use our Kaitai parser.
        try:
            client_hello = tls.ClientHello.from_file(self.rfile)
        except exceptions.TlsProtocolException:  # pragma: no cover
            pass  # if this fails, we don't want everything to go down.
        else:
            self.tls_extensions = client_hello.extensions

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
        return "<ServerConnection: {tls}{alpn}{address}>".format(
            tls=tls,
            alpn=alpn,
            address=human.format_address(self.address),
        )

    def __eq__(self, other):
        if isinstance(other, ServerConnection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    # Sans-io attributes.
    state = 0
    error = None
    tls = None
    certificate_list = ()
    alpn_offers = None
    cipher_name = None
    cipher_list = None
    via2 = None

    _stateobject_attributes = dict(
        id=str,
        address=tuple,
        ip_address=tuple,
        source_address=tuple,
        tls_established=bool,
        sni=str,
        alpn_proto_negotiated=bytes,
        tls_version=str,
        timestamp_start=float,
        timestamp_tcp_setup=float,
        timestamp_tls_setup=float,
        timestamp_end=float,
        # sans-io exclusives
        state=int,
        error=str,
        tls=bool,
        certificate_list=typing.List[certs.Cert],
        alpn_offers=typing.List[bytes],
        cipher_name=str,
        cipher_list=typing.List[str],
        via2=None,
    )

    @property
    def cert(self) -> typing.Optional[certs.Cert]:  # pragma: no cover
        warnings.warn(".cert is deprecated, use .certificate_list instead.", PendingDeprecationWarning)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @cert.setter
    def cert(self, val):  # pragma: no cover
        warnings.warn(".cert is deprecated, use .certificate_list instead.", PendingDeprecationWarning)
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []

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
            sni=address[0],
            alpn_proto_negotiated=None,
            tls_version=None,
            source_address=('', 0),
            tls_established=False,
            timestamp_start=None,
            timestamp_tcp_setup=None,
            timestamp_tls_setup=None,
            timestamp_end=None,
            via=None,
            state=0,
            error=None,
            tls=False,
            certificate_list=[],
            alpn_offers=[],
            cipher_name=None,
            cipher_list=[],
            via2=None,
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

    def establish_tls(self, *, sni=None, client_certs=None, **kwargs):
        if sni and not isinstance(sni, str):
            raise ValueError("sni must be str, not " + type(sni).__name__)
        client_cert = None
        if client_certs:
            client_certs = os.path.expanduser(client_certs)
            if os.path.isfile(client_certs):
                client_cert = client_certs
            else:
                path = os.path.join(
                    client_certs,
                    (sni or self.address[0].encode("idna").decode()) + ".pem"
                )
                if os.path.exists(path):
                    client_cert = path

        self.convert_to_tls(cert=client_cert, sni=sni, **kwargs)
        self.sni = sni
        self.alpn_proto_negotiated = self.get_alpn_proto_negotiated()
        self.tls_version = self.connection.get_protocol_version_name()
        self.timestamp_tls_setup = time.time()

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = time.time()


ServerConnection._stateobject_attributes["via"] = ServerConnection
