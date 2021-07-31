import ssl
import typing

import pytest

from OpenSSL import SSL
from mitmproxy import connection
from mitmproxy.connection import ConnectionState, Server
from mitmproxy.proxy import commands, context, events, layer
from mitmproxy.proxy.layers import tls
from mitmproxy.utils import data
from test.mitmproxy.proxy import tutils

tlsdata = data.Data(__name__)


def test_is_tls_handshake_record():
    assert tls.is_tls_handshake_record(bytes.fromhex("160300"))
    assert tls.is_tls_handshake_record(bytes.fromhex("160301"))
    assert tls.is_tls_handshake_record(bytes.fromhex("160302"))
    assert tls.is_tls_handshake_record(bytes.fromhex("160303"))
    assert not tls.is_tls_handshake_record(bytes.fromhex("ffffff"))
    assert not tls.is_tls_handshake_record(bytes.fromhex(""))
    assert not tls.is_tls_handshake_record(bytes.fromhex("160304"))
    assert not tls.is_tls_handshake_record(bytes.fromhex("150301"))


def test_record_contents():
    data = bytes.fromhex(
        "1603010002beef"
        "1603010001ff"
    )
    assert list(tls.handshake_record_contents(data)) == [
        b"\xbe\xef", b"\xff"
    ]
    for i in range(6):
        assert list(tls.handshake_record_contents(data[:i])) == []


def test_record_contents_err():
    with pytest.raises(ValueError, match="Expected TLS record"):
        next(tls.handshake_record_contents(b"GET /error"))

    empty_record = bytes.fromhex("1603010000")
    with pytest.raises(ValueError, match="Record must not be empty"):
        next(tls.handshake_record_contents(empty_record))


client_hello_no_extensions = bytes.fromhex(
    "0100006103015658a756ab2c2bff55f636814deac086b7ca56b65058c7893ffc6074f5245f70205658a75475103a152637"
    "78e1bb6d22e8bbd5b6b0a3a59760ad354e91ba20d353001a0035002f000a000500040009000300060008006000"
    "61006200640100"
)
client_hello_with_extensions = bytes.fromhex(
    "16030300bb"  # record layer
    "010000b7"  # handshake layer
    "03033b70638d2523e1cba15f8364868295305e9c52aceabda4b5147210abc783e6e1000022c02bc02fc02cc030"
    "cca9cca8cc14cc13c009c013c00ac014009c009d002f0035000a0100006cff0100010000000010000e00000b65"
    "78616d706c652e636f6d0017000000230000000d00120010060106030501050304010403020102030005000501"
    "00000000001200000010000e000c02683208687474702f312e3175500000000b00020100000a00080006001d00"
    "170018"
)


def test_get_client_hello():
    single_record = bytes.fromhex("1603010065") + client_hello_no_extensions
    assert tls.get_client_hello(single_record) == client_hello_no_extensions

    split_over_two_records = (
            bytes.fromhex("1603010020") + client_hello_no_extensions[:32] +
            bytes.fromhex("1603010045") + client_hello_no_extensions[32:]
    )
    assert tls.get_client_hello(split_over_two_records) == client_hello_no_extensions

    incomplete = split_over_two_records[:42]
    assert tls.get_client_hello(incomplete) is None


def test_parse_client_hello():
    assert tls.parse_client_hello(client_hello_with_extensions).sni == "example.com"
    assert tls.parse_client_hello(client_hello_with_extensions[:50]) is None
    with pytest.raises(ValueError):
        tls.parse_client_hello(client_hello_with_extensions[:183] + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00')


class SSLTest:
    """Helper container for Python's builtin SSL object."""

    def __init__(self, server_side: bool = False, alpn: typing.Optional[typing.List[str]] = None,
                 sni: typing.Optional[bytes] = b"example.mitmproxy.org"):
        self.inc = ssl.MemoryBIO()
        self.out = ssl.MemoryBIO()
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT)

        self.ctx.verify_mode = ssl.CERT_OPTIONAL
        self.ctx.load_verify_locations(
            cafile=tlsdata.path("../../net/data/verificationcerts/trusted-root.crt"),
        )

        if alpn:
            self.ctx.set_alpn_protocols(alpn)
        if server_side:
            self.ctx.load_cert_chain(
                certfile=tlsdata.path("../../net/data/verificationcerts/trusted-leaf.crt"),
                keyfile=tlsdata.path("../../net/data/verificationcerts/trusted-leaf.key"),
            )

        self.obj = self.ctx.wrap_bio(
            self.inc,
            self.out,
            server_hostname=None if server_side else sni,
            server_side=server_side,
        )

    def bio_write(self, buf: bytes) -> int:
        return self.inc.write(buf)

    def bio_read(self, bufsize: int = 2 ** 16) -> bytes:
        return self.out.read(bufsize)

    def do_handshake(self) -> None:
        return self.obj.do_handshake()


def _test_echo(playbook: tutils.Playbook, tssl: SSLTest, conn: connection.Connection) -> None:
    tssl.obj.write(b"Hello World")
    data = tutils.Placeholder(bytes)
    assert (
            playbook
            >> events.DataReceived(conn, tssl.bio_read())
            << commands.SendData(conn, data)
    )
    tssl.bio_write(data())
    assert tssl.obj.read() == b"hello world"


class TlsEchoLayer(tutils.EchoLayer):
    err: typing.Optional[str] = None

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived) and event.data == b"open-connection":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.SendData(event.connection, f"open-connection failed: {err}".encode())
        else:
            yield from super()._handle_event(event)


def interact(playbook: tutils.Playbook, conn: connection.Connection, tssl: SSLTest):
    data = tutils.Placeholder(bytes)
    assert (
            playbook
            >> events.DataReceived(conn, tssl.bio_read())
            << commands.SendData(conn, data)
    )
    tssl.bio_write(data())


def reply_tls_start_client(alpn: typing.Optional[bytes] = None, *args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for tls_start_client hooks.
    """

    def make_client_conn(tls_start: tls.TlsStartData) -> None:
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        ssl_context.use_privatekey_file(
            tlsdata.path("../../net/data/verificationcerts/trusted-leaf.key")
        )
        ssl_context.use_certificate_chain_file(
            tlsdata.path("../../net/data/verificationcerts/trusted-leaf.crt")
        )
        if alpn is not None:
            ssl_context.set_alpn_select_callback(lambda conn, protos: alpn)

        tls_start.ssl_conn = SSL.Connection(ssl_context)
        tls_start.ssl_conn.set_accept_state()

    return tutils.reply(*args, side_effect=make_client_conn, **kwargs)


def reply_tls_start_server(alpn: typing.Optional[bytes] = None, *args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for tls_start_server hooks.
    """

    def make_server_conn(tls_start: tls.TlsStartData) -> None:
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        ssl_context.load_verify_locations(
            cafile=tlsdata.path("../../net/data/verificationcerts/trusted-root.crt")
        )
        if alpn is not None:
            ssl_context.set_alpn_protos([alpn])
        ssl_context.set_verify(SSL.VERIFY_PEER)

        tls_start.ssl_conn = SSL.Connection(ssl_context)
        tls_start.ssl_conn.set_connect_state()
        # Set SNI
        tls_start.ssl_conn.set_tlsext_host_name(tls_start.conn.sni.encode())

        # Manually enable hostname verification.
        # Recent OpenSSL versions provide slightly nicer ways to do this, but they are not exposed in
        # cryptography and likely a PITA to add.
        # https://wiki.openssl.org/index.php/Hostname_validation
        param = SSL._lib.SSL_get0_param(tls_start.ssl_conn._ssl)
        # Common Name matching is disabled in both Chrome and Firefox, so we should disable it, too.
        # https://www.chromestatus.com/feature/4981025180483584
        SSL._lib.X509_VERIFY_PARAM_set_hostflags(
            param,
            SSL._lib.X509_CHECK_FLAG_NO_PARTIAL_WILDCARDS | SSL._lib.X509_CHECK_FLAG_NEVER_CHECK_SUBJECT
        )
        SSL._openssl_assert(
            SSL._lib.X509_VERIFY_PARAM_set1_host(param, tls_start.conn.sni.encode(), 0) == 1
        )

    return tutils.reply(*args, side_effect=make_server_conn, **kwargs)


class TestServerTLS:
    def test_repr(self, tctx):
        assert repr(tls.ServerTLSLayer(tctx))

    def test_not_connected(self, tctx: context.Context):
        """Test that we don't do anything if no server connection exists."""
        layer = tls.ServerTLSLayer(tctx)
        layer.child_layer = TlsEchoLayer(tctx)

        assert (
                tutils.Playbook(layer)
                >> events.DataReceived(tctx.client, b"Hello World")
                << commands.SendData(tctx.client, b"hello world")
        )

    def test_simple(self, tctx):
        playbook = tutils.Playbook(tls.ServerTLSLayer(tctx))
        tctx.server.address = ("example.mitmproxy.org", 443)
        tctx.server.state = ConnectionState.OPEN
        tctx.server.sni = "example.mitmproxy.org"

        tssl = SSLTest(server_side=True)

        # send ClientHello
        data = tutils.Placeholder(bytes)
        assert (
                playbook
                << tls.TlsStartServerHook(tutils.Placeholder())
                >> reply_tls_start_server()
                << commands.SendData(tctx.server, data)
        )

        # receive ServerHello, finish client handshake
        tssl.bio_write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl.do_handshake()
        interact(playbook, tctx.server, tssl)

        # finish server handshake
        tssl.do_handshake()
        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl.bio_read())
                << None
        )

        assert tctx.server.tls_established

        # Echo
        assert (
                playbook
                >> events.DataReceived(tctx.client, b"foo")
                << layer.NextLayerHook(tutils.Placeholder())
                >> tutils.reply_next_layer(TlsEchoLayer)
                << commands.SendData(tctx.client, b"foo")
        )
        _test_echo(playbook, tssl, tctx.server)

        with pytest.raises(ssl.SSLWantReadError):
            tssl.obj.unwrap()
        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl.bio_read())
                << commands.CloseConnection(tctx.server)
                >> events.ConnectionClosed(tctx.server)
                << None
        )

    def test_untrusted_cert(self, tctx):
        """If the certificate is not trusted, we should fail."""
        playbook = tutils.Playbook(tls.ServerTLSLayer(tctx))
        tctx.server.address = ("wrong.host.mitmproxy.org", 443)
        tctx.server.sni = "wrong.host.mitmproxy.org"

        tssl = SSLTest(server_side=True)

        # send ClientHello
        data = tutils.Placeholder(bytes)
        assert (
                playbook
                >> events.DataReceived(tctx.client, b"open-connection")
                << layer.NextLayerHook(tutils.Placeholder())
                >> tutils.reply_next_layer(TlsEchoLayer)
                << commands.OpenConnection(tctx.server)
                >> tutils.reply(None)
                << tls.TlsStartServerHook(tutils.Placeholder())
                >> reply_tls_start_server()
                << commands.SendData(tctx.server, data)
        )

        # receive ServerHello, finish client handshake
        tssl.bio_write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl.do_handshake()

        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl.bio_read())
                << commands.Log("Server TLS handshake failed. Certificate verify failed: Hostname mismatch", "warn")
                << commands.CloseConnection(tctx.server)
                << commands.SendData(tctx.client,
                                     b"open-connection failed: Certificate verify failed: Hostname mismatch")
        )
        assert not tctx.server.tls_established

    def test_remote_speaks_no_tls(self, tctx):
        playbook = tutils.Playbook(tls.ServerTLSLayer(tctx))
        tctx.server.state = ConnectionState.OPEN
        tctx.server.sni = "example.mitmproxy.org"

        # send ClientHello, receive random garbage back
        data = tutils.Placeholder(bytes)
        assert (
                playbook
                << tls.TlsStartServerHook(tutils.Placeholder())
                >> reply_tls_start_server()
                << commands.SendData(tctx.server, data)
                >> events.DataReceived(tctx.server, b"HTTP/1.1 404 Not Found\r\n")
                << commands.Log("Server TLS handshake failed. The remote server does not speak TLS.", "warn")
                << commands.CloseConnection(tctx.server)
        )


def make_client_tls_layer(
        tctx: context.Context,
        **kwargs
) -> typing.Tuple[tutils.Playbook, tls.ClientTLSLayer, SSLTest]:
    # This is a bit contrived as the client layer expects a server layer as parent.
    # We also set child layers manually to avoid NextLayer noise.
    server_layer = tls.ServerTLSLayer(tctx)
    client_layer = tls.ClientTLSLayer(tctx)
    server_layer.child_layer = client_layer
    client_layer.child_layer = TlsEchoLayer(tctx)
    playbook = tutils.Playbook(server_layer)

    # Add some server config, this is needed anyways.
    tctx.server.__dict__["address"] = ("example.mitmproxy.org", 443)  # .address fails because connection is open
    tctx.server.sni = "example.mitmproxy.org"

    tssl_client = SSLTest(**kwargs)
    # Start handshake.
    with pytest.raises(ssl.SSLWantReadError):
        tssl_client.do_handshake()

    return playbook, client_layer, tssl_client


class TestClientTLS:
    def test_client_only(self, tctx: context.Context):
        """Test TLS with client only"""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)
        client_layer.debug = "  "
        assert not tctx.client.tls_established

        # Send ClientHello, receive ServerHello
        data = tutils.Placeholder(bytes)
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl_client.bio_read())
                << tls.TlsClienthelloHook(tutils.Placeholder())
                >> tutils.reply()
                << tls.TlsStartClientHook(tutils.Placeholder())
                >> reply_tls_start_client()
                << commands.SendData(tctx.client, data)
        )
        tssl_client.bio_write(data())
        tssl_client.do_handshake()
        # Finish Handshake
        interact(playbook, tctx.client, tssl_client)

        assert tssl_client.obj.getpeercert(True)
        assert tctx.client.tls_established

        # Echo
        _test_echo(playbook, tssl_client, tctx.client)
        other_server = Server(None)
        assert (
                playbook
                >> events.DataReceived(other_server, b"Plaintext")
                << commands.SendData(other_server, b"plaintext")
        )

    @pytest.mark.parametrize("eager", ["eager", ""])
    def test_server_required(self, tctx, eager):
        """
        Test the scenario where a server connection is required (for example, because of an unknown ALPN)
        to establish TLS with the client.
        """
        if eager:
            tctx.server.state = ConnectionState.OPEN
        tssl_server = SSLTest(server_side=True, alpn=["quux"])
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx, alpn=["quux"])

        # We should now get instructed to open a server connection.
        data = tutils.Placeholder(bytes)

        def require_server_conn(client_hello: tls.ClientHelloData) -> None:
            client_hello.establish_server_tls_first = True

        (
                playbook
                >> events.DataReceived(tctx.client, tssl_client.bio_read())
                << tls.TlsClienthelloHook(tutils.Placeholder())
                >> tutils.reply(side_effect=require_server_conn)
        )
        if not eager:
            (
                playbook
                << commands.OpenConnection(tctx.server)
                >> tutils.reply(None)
            )
        assert (
            playbook
            << tls.TlsStartServerHook(tutils.Placeholder())
            >> reply_tls_start_server(alpn=b"quux")
            << commands.SendData(tctx.server, data)
        )

        # Establish TLS with the server...
        tssl_server.bio_write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl_server.do_handshake()

        data = tutils.Placeholder(bytes)
        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl_server.bio_read())
                << commands.SendData(tctx.server, data)
                << tls.TlsStartClientHook(tutils.Placeholder())
        )
        tssl_server.bio_write(data())
        assert tctx.server.tls_established
        # Server TLS is established, we can now reply to the client handshake...

        data = tutils.Placeholder(bytes)
        assert (
                playbook
                >> reply_tls_start_client(alpn=b"quux")
                << commands.SendData(tctx.client, data)
        )
        tssl_client.bio_write(data())
        tssl_client.do_handshake()
        interact(playbook, tctx.client, tssl_client)

        # Both handshakes completed!
        assert tctx.client.tls_established
        assert tctx.server.tls_established
        assert tctx.server.sni == tctx.client.sni
        assert tctx.client.alpn == b"quux"
        assert tctx.server.alpn == b"quux"
        _test_echo(playbook, tssl_server, tctx.server)
        _test_echo(playbook, tssl_client, tctx.client)

    def test_cannot_parse_clienthello(self, tctx: context.Context):
        """Test the scenario where we cannot parse the ClientHello"""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)

        invalid = b"\x16\x03\x01\x00\x00"

        assert (
                playbook
                >> events.DataReceived(tctx.client, invalid)
                << commands.Log(f"Client TLS handshake failed. Cannot parse ClientHello: {invalid.hex()}", level="warn")
                << commands.CloseConnection(tctx.client)
        )
        assert not tctx.client.tls_established

        # Make sure that an active server connection does not cause child layers to spawn.
        client_layer.debug = ""
        assert (
            playbook
            >> events.DataReceived(Server(None), b"data on other stream")
            << commands.Log(">> DataReceived(server, b'data on other stream')", 'debug')
            << commands.Log("Swallowing DataReceived(server, b'data on other stream') as handshake failed.", "debug")
        )

    def test_mitmproxy_ca_is_untrusted(self, tctx: context.Context):
        """Test the scenario where the client doesn't trust the mitmproxy CA."""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx, sni=b"wrong.host.mitmproxy.org")
        playbook.logs = True

        data = tutils.Placeholder(bytes)
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl_client.bio_read())
                << tls.TlsClienthelloHook(tutils.Placeholder())
                >> tutils.reply()
                << tls.TlsStartClientHook(tutils.Placeholder())
                >> reply_tls_start_client()
                << commands.SendData(tctx.client, data)
        )
        tssl_client.bio_write(data())
        with pytest.raises(ssl.SSLCertVerificationError):
            tssl_client.do_handshake()
        # Finish Handshake
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl_client.bio_read())
                << commands.Log("Client TLS handshake failed. The client does not trust the proxy's certificate "
                                "for wrong.host.mitmproxy.org (sslv3 alert bad certificate)", "warn")
                << commands.CloseConnection(tctx.client)
                >> events.ConnectionClosed(tctx.client)
        )
        assert not tctx.client.tls_established

    @pytest.mark.parametrize("close_at", ["tls_clienthello", "tls_start_client", "handshake"])
    def test_immediate_disconnect(self, tctx: context.Context, close_at):
        """Test the scenario where the client is disconnecting during the handshake.
        This may happen because they are not interested in the connection anymore, or because they do not like
        the proxy certificate."""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx, sni=b"wrong.host.mitmproxy.org")
        playbook.logs = True

        playbook >> events.DataReceived(tctx.client, tssl_client.bio_read())
        playbook << tls.TlsClienthelloHook(tutils.Placeholder())

        if close_at == "tls_clienthello":
            assert (
                playbook
                >> events.ConnectionClosed(tctx.client)
                >> tutils.reply(to=-2)
                << tls.TlsStartClientHook(tutils.Placeholder())
                >> reply_tls_start_client()
                << commands.CloseConnection(tctx.client)
            )
            return

        playbook >> tutils.reply()
        playbook << tls.TlsStartClientHook(tutils.Placeholder())

        if close_at == "tls_start_client":
            assert (
                playbook
                >> events.ConnectionClosed(tctx.client)
                >> reply_tls_start_client(to=-2)
                << commands.CloseConnection(tctx.client)
            )
            return

        assert (
            playbook
            >> reply_tls_start_client()
            << commands.SendData(tctx.client, tutils.Placeholder())
            >> events.ConnectionClosed(tctx.client)
            << commands.Log("Client TLS handshake failed. The client disconnected during the handshake. "
                            "If this happens consistently for wrong.host.mitmproxy.org, this may indicate that the "
                            "client does not trust the proxy's certificate.", "info")
            << commands.CloseConnection(tctx.client)
        )
