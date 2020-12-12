import struct
import time
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy.net import tls as net_tls
from mitmproxy.proxy2 import commands, events, layer, tunnel
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.commands import Hook
from mitmproxy.utils import human


def is_tls_handshake_record(d: bytes) -> bool:
    """
    Returns:
        True, if the passed bytes start with the TLS record magic bytes
        False, otherwise.
    """
    # TLS ClientHello magic, works for SSLv3, TLSv1.0, TLSv1.1, TLSv1.2.
    # TLS 1.3 mandates legacy_record_version to be 0x0301.
    # http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
    return (
            len(d) >= 3 and
            d[0] == 0x16 and
            d[1] == 0x03 and
            0x0 <= d[2] <= 0x03
    )


def handshake_record_contents(data: bytes) -> Iterator[bytes]:
    """
    Returns a generator that yields the bytes contained in each handshake record.
    This will raise an error on the first non-handshake record, so fully exhausting this
    generator is a bad idea.
    """
    offset = 0
    while True:
        if len(data) < offset + 5:
            return
        record_header = data[offset:offset + 5]
        if not is_tls_handshake_record(record_header):
            raise ValueError(f"Expected TLS record, got {record_header} instead.")
        record_size = struct.unpack("!H", record_header[3:])[0]
        if record_size == 0:
            raise ValueError("Record must not be empty.")
        offset += 5

        if len(data) < offset + record_size:
            return
        record_body = data[offset:offset + record_size]
        yield record_body
        offset += record_size


def get_client_hello(data: bytes) -> Optional[bytes]:
    """
    Read all TLS records that contain the initial ClientHello.
    Returns the raw handshake packet bytes, without TLS record headers.
    """
    client_hello = b""
    for d in handshake_record_contents(data):
        client_hello += d
        if len(client_hello) >= 4:
            client_hello_size = struct.unpack("!I", b'\x00' + client_hello[1:4])[0] + 4
            if len(client_hello) >= client_hello_size:
                return client_hello[:client_hello_size]
    return None


def parse_client_hello(data: bytes) -> Optional[net_tls.ClientHello]:
    """
    Check if the supplied bytes contain a full ClientHello message,
    and if so, parse it.

    Returns:
        - A ClientHello object on success
        - None, if the TLS record is not complete

    Raises:
        - A ValueError, if the passed ClientHello is invalid
    """
    # Check if ClientHello is complete
    client_hello = get_client_hello(data)
    if client_hello:
        return net_tls.ClientHello(client_hello[4:])
    return None


HTTP1_ALPNS = (b"http/1.1", b"http/1.0", b"http/0.9")
HTTP_ALPNS = (b"h2",) + HTTP1_ALPNS


# We need these classes as hooks can only have one argument at the moment.

@dataclass
class TlsStartData:
    conn: context.Connection
    context: context.Context
    ssl_conn: Optional[SSL.Connection] = None


@dataclass
class ClientHelloData:
    context: context.Context
    establish_server_tls_first: bool = False


class TlsStartHook(Hook):
    data: TlsStartData


class TlsClienthelloHook(Hook):
    data: ClientHelloData


class _TLSLayer(tunnel.TunnelLayer):
    tls: SSL.Connection = None
    """The OpenSSL connection object"""

    def __init__(self, context: context.Context, conn: context.Connection):
        super().__init__(
            context,
            tunnel_connection=conn,
            conn=conn,
        )

        assert not conn.tls
        conn.tls = True

    def __repr__(self):
        return super().__repr__().replace(")", f" {self.conn.sni} {self.conn.alpn})")

    def start_tls(self) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        assert not self.tls

        tls_start = TlsStartData(self.conn, self.context)
        yield TlsStartHook(tls_start)
        assert tls_start.ssl_conn
        self.tls = tls_start.ssl_conn

    def tls_interact(self) -> layer.CommandGenerator[None]:
        while True:
            try:
                data = self.tls.bio_read(65535)
            except SSL.WantReadError:
                return  # Okay, nothing more waiting to be sent.
            else:
                yield commands.SendData(self.conn, data)

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        # bio_write errors for b"", so we need to check first if we actually received something.
        if data:
            self.tls.bio_write(data)
        try:
            self.tls.do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact()
            return False, None
        except SSL.Error as e:
            # provide more detailed information for some errors.
            last_err = e.args and isinstance(e.args[0], list) and e.args[0] and e.args[0][-1]
            if last_err == ('SSL routines', 'tls_process_server_certificate', 'certificate verify failed'):
                verify_result = SSL._lib.SSL_get_verify_result(self.tls._ssl)
                error = SSL._ffi.string(SSL._lib.X509_verify_cert_error_string(verify_result)).decode()
                err = f"Certificate verify failed: {error}"
            elif last_err in [
                ('SSL routines', 'ssl3_read_bytes', 'tlsv1 alert unknown ca'),
                ('SSL routines', 'ssl3_read_bytes', 'sslv3 alert bad certificate')
            ]:
                err = last_err[2]
            elif last_err == ('SSL routines', 'ssl3_get_record', 'wrong version number') and data[:4].isascii():
                err = f"The remote server does not speak TLS."
            else:
                err = repr(e)
            return False, err
        else:
            # Get all peer certificates.
            # https://www.openssl.org/docs/man1.1.1/man3/SSL_get_peer_cert_chain.html
            # If called on the client side, the stack also contains the peer's certificate; if called on the server
            # side, the peer's certificate must be obtained separately using SSL_get_peer_certificate(3).
            all_certs = self.tls.get_peer_cert_chain() or []
            if self.conn == self.context.client:
                cert = self.tls.get_peer_certificate()
                if cert:
                    all_certs.insert(0, cert)

            self.conn.tls_established = True
            self.conn.sni = self.tls.get_servername()
            self.conn.alpn = self.tls.get_alpn_proto_negotiated()
            self.conn.certificate_list = [certs.Cert(x) for x in all_certs]
            self.conn.cipher_list = self.tls.get_cipher_list()
            self.conn.tls_version = self.tls.get_protocol_version_name()
            self.conn.timestamp_tls_setup = time.time()
            yield commands.Log(f"TLS established: {self.conn}")
            yield from self.receive_data(b"")
            return True, None

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        if data:
            self.tls.bio_write(data)
        yield from self.tls_interact()

        plaintext = bytearray()
        close = False
        while True:
            try:
                plaintext.extend(self.tls.recv(65535))
            except SSL.WantReadError:
                break
            except SSL.ZeroReturnError:
                close = True
                break

        if plaintext:
            yield from self.event_to_child(
                events.DataReceived(self.conn, bytes(plaintext))
            )
        if close:
            self.conn.state &= ~context.ConnectionState.CAN_READ
            yield commands.Log(f"TLS close_notify {self.conn}", level="debug")
            yield from self.event_to_child(
                events.ConnectionClosed(self.conn)
            )

    def receive_close(self) -> layer.CommandGenerator[None]:
        if self.tls.get_shutdown() & SSL.RECEIVED_SHUTDOWN:
            pass  # We have already dispatched a ConnectionClosed to the child layer.
        else:
            yield from super().receive_close()

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        self.tls.sendall(data)
        yield from self.tls_interact()

    def send_close(self) -> layer.CommandGenerator[None]:
        # We should probably shutdown the TLS connection properly here.
        yield from super().send_close()


class ServerTLSLayer(_TLSLayer):
    """
    This layer establishes TLS for a single server connection.
    """
    command_to_reply_to: Optional[commands.OpenConnection] = None

    def __init__(self, context: context.Context):
        super().__init__(context, context.server)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self.start_tls()
        yield from self.receive_handshake_data(b"")

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.Log(f"Server TLS handshake failed. {err}", level="warn")
        yield from super().on_handshake_error(err)


class ClientTLSLayer(_TLSLayer):
    """
    This layer establishes TLS on a single client connection.

    ┌─────┐
    │Start│
    └┬────┘
     ↓
    ┌────────────────────┐
    │Wait for ClientHello│
    └┬───────────────────┘
     ↓
    ┌────────────────┐
    │Process messages│
    └────────────────┘

    """
    recv_buffer: bytearray
    server_tls_available: bool

    def __init__(self, context: context.Context):
        super().__init__(context, context.client)
        self.server_tls_available = isinstance(self.context.layers[-2], ServerTLSLayer)
        self.recv_buffer = bytearray()

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from ()

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        self.recv_buffer.extend(data)
        try:
            client_hello = parse_client_hello(self.recv_buffer)
        except ValueError:
            return False, f"Cannot parse ClientHello: {self.recv_buffer.hex()}"

        if not client_hello:
            return False, None

        self.conn.sni = client_hello.sni
        self.conn.alpn_offers = client_hello.alpn_protocols
        tls_clienthello = ClientHelloData(self.context)
        yield TlsClienthelloHook(tls_clienthello)

        if tls_clienthello.establish_server_tls_first and not self.context.server.tls_established:
            err = yield from self.start_server_tls()
            if err:
                yield commands.Log(f"Unable to establish TLS connection with server ({err}). "
                                   f"Trying to establish TLS with client anyway.")

        yield from self.start_tls()

        self.receive_handshake_data = super().receive_handshake_data
        ret = yield from self.receive_handshake_data(bytes(self.recv_buffer))
        self.recv_buffer.clear()
        return ret

    def start_server_tls(self) -> layer.CommandGenerator[Optional[str]]:
        """
        We often need information from the upstream connection to establish TLS with the client.
        For example, we need to check if the client does ALPN or not.
        """
        if not self.server_tls_available:
            return "No server TLS available."
        err = yield commands.OpenConnection(self.context.server)
        return err

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        if self.conn.sni:
            dest = self.conn.sni.decode("idna")
        else:
            dest = human.format_address(self.context.server.address)
        if err.startswith("Cannot parse ClientHello"):
            pass
        elif "unknown ca" in err or "bad certificate" in err:
            err = f"The client does not trust the proxy's certificate for {dest} ({err})"
        else:
            err = f"The client may not trust the proxy's certificate for {dest} ({err})"
        yield commands.Log(f"Client TLS handshake failed. {err}", level="warn")
        yield from super().on_handshake_error(err)


class MockTLSLayer(_TLSLayer):
    """Mock layer to disable actual TLS and use cleartext in tests.

    Use like so:
        monkeypatch.setattr(tls, "ServerTLSLayer", tls.MockTLSLayer)
    """

    def __init__(self, ctx: context.Context):
        super().__init__(ctx, context.Server(None))
