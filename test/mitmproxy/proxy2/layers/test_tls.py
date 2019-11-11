import os
import ssl
import typing

import pytest
from OpenSSL import SSL

from mitmproxy.proxy2 import commands, context, events
from mitmproxy.proxy2.layers import tls
from mitmproxy.utils import data
from test.mitmproxy.proxy2 import tutils

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


class SSLTest:
    """Helper container for Python's builtin SSL object."""

    def __init__(self, server_side: bool = False, alpn: typing.List[bytes] = None,
                 sni: typing.Optional[bytes] = b"example.com"):
        self.inc = ssl.MemoryBIO()
        self.out = ssl.MemoryBIO()
        self.ctx = ssl.SSLContext()
        if alpn:
            self.ctx.set_alpn_protocols(alpn)
        if server_side:
            # FIXME: Replace hardcoded location
            self.ctx.load_cert_chain(os.path.expanduser("~/.mitmproxy/mitmproxy-ca.pem"))
        self.obj = self.ctx.wrap_bio(
            self.inc,
            self.out,
            server_hostname=None if server_side else sni,
            server_side=server_side,
        )


def _test_echo(playbook: tutils.playbook, tssl: SSLTest, conn: context.Connection) -> None:
    tssl.obj.write(b"Hello World")
    data = tutils.Placeholder()
    assert (
            playbook
            >> events.DataReceived(conn, tssl.out.read())
            << commands.SendData(conn, data)
    )
    tssl.inc.write(data())
    assert tssl.obj.read() == b"hello world"


class TlsEchoLayer(tutils.EchoLayer):
    err: typing.Optional[str] = None

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived) and event.data == b"establish-server-tls":
            # noinspection PyTypeChecker
            self.err = yield tls.EstablishServerTLS(self.context.server)
        else:
            yield from super()._handle_event(event)


def interact(playbook: tutils.playbook, conn: context.Connection, tssl: SSLTest):
    data = tutils.Placeholder()
    assert (
            playbook
            >> events.DataReceived(conn, tssl.out.read())
            << commands.SendData(conn, data)
    )
    tssl.inc.write(data())


def reply_tls_start(*args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for tls_start hooks.
    """

    def make_conn(hook: commands.Hook) -> None:
        tls_start = hook.data
        assert isinstance(tls_start, tls.TlsStart)
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        if tls_start.conn == tls_start.context.client:
            ssl_context.use_privatekey_file(
                tlsdata.path("../../net/data/verificationcerts/trusted-leaf.key")
            )
            ssl_context.use_certificate_chain_file(
                tlsdata.path("../../net/data/verificationcerts/trusted-leaf.crt")
            )
        tls_start.ssl_conn = SSL.Connection(ssl_context)

    return tutils.reply(*args, side_effect=make_conn, **kwargs)


class TestServerTLS:
    def test_no_tls(self, tctx: context.Context):
        """Test TLS layer without TLS"""
        layer = tls.ServerTLSLayer(tctx)
        layer.child_layer = TlsEchoLayer(tctx)

        # Handshake
        assert (
                tutils.playbook(layer)
                >> events.DataReceived(tctx.client, b"Hello World")
                << commands.SendData(tctx.client, b"hello world")
                >> events.DataReceived(tctx.server, b"Foo")
                << commands.SendData(tctx.server, b"foo")
        )

    def test_simple(self, tctx):
        layer = tls.ServerTLSLayer(tctx)
        playbook = tutils.playbook(layer)
        tctx.server.connected = True
        tctx.server.address = ("example.com", 443)

        tssl = SSLTest(server_side=True)

        # send ClientHello
        data = tutils.Placeholder()
        assert (
                playbook
                >> events.DataReceived(tctx.client, b"establish-server-tls")
                << commands.Hook("next_layer", tutils.Placeholder())
                >> tutils.next_layer(TlsEchoLayer)
                << commands.Hook("tls_start", tutils.Placeholder())
                >> reply_tls_start()
                << commands.SendData(tctx.server, data)
        )

        # receive ServerHello, finish client handshake
        tssl.inc.write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl.obj.do_handshake()
        interact(playbook, tctx.server, tssl)

        # finish server handshake
        tssl.obj.do_handshake()
        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl.out.read())
                << None
        )

        assert tctx.server.tls_established

        # Echo
        _test_echo(playbook, tssl, tctx.server)


def _make_client_tls_layer(tctx: context.Context) -> typing.Tuple[tutils.playbook, tls.ClientTLSLayer]:
    # This is a bit contrived as the client layer expects a server layer as parent.
    # We also set child layers manually to avoid NextLayer noise.
    server_layer = tls.ServerTLSLayer(tctx)
    client_layer = tls.ClientTLSLayer(tctx)
    server_layer.child_layer = client_layer
    client_layer.child_layer = TlsEchoLayer(tctx)
    playbook = tutils.playbook(server_layer)
    return playbook, client_layer


def _test_tls_client_server(
        tctx: context.Context,
        sni: typing.Optional[bytes]
) -> typing.Tuple[tutils.playbook, tls.ClientTLSLayer, SSLTest]:
    playbook, client_layer = _make_client_tls_layer(tctx)
    tctx.server.tls = True
    tctx.server.address = ("example.com", 443)
    tssl_client = SSLTest(sni=sni)

    # Send ClientHello
    with pytest.raises(ssl.SSLWantReadError):
        tssl_client.obj.do_handshake()

    return playbook, client_layer, tssl_client


class TestClientTLS:
    def test_client_only(self, tctx: context.Context):
        """Test TLS with client only"""
        playbook, client_layer = _make_client_tls_layer(tctx)
        tssl = SSLTest()
        assert not tctx.client.tls_established

        # Start Handshake, send ClientHello and ServerHello
        with pytest.raises(ssl.SSLWantReadError):
            tssl.obj.do_handshake()
        data = tutils.Placeholder()
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl.out.read())
                << commands.Hook("tls_start", tutils.Placeholder())
                >> reply_tls_start()
                << commands.SendData(tctx.client, data)
        )
        tssl.inc.write(data())
        tssl.obj.do_handshake()
        # Finish Handshake
        interact(playbook, tctx.client, tssl)

        assert tssl.obj.getpeercert(True)
        assert tctx.client.tls_established

        # Echo
        _test_echo(playbook, tssl, tctx.client)
        assert (
                playbook
                >> events.DataReceived(tctx.server, b"Plaintext")
                << commands.SendData(tctx.server, b"plaintext")
        )

    def test_server_not_required(self, tctx):
        """
        Here we test the scenario where a server connection is _not_ required
        to establish TLS with the client. After determining this when parsing the ClientHello,
        we only establish a connection with the client. The server connection may ultimately
        be established when OpenConnection is called.
        """
        playbook, client_layer, tssl = _test_tls_client_server(tctx, sni=b"example.com")
        data = tutils.Placeholder()
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl.out.read())
                << commands.Hook("tls_start", tutils.Placeholder())
                >> reply_tls_start()
                << commands.SendData(tctx.client, data)
        )
        tssl.inc.write(data())
        tssl.obj.do_handshake()
        interact(playbook, tctx.client, tssl)
        assert tctx.client.tls_established

    def test_server_required(self, tctx):
        """
        Here we test the scenario where a server connection is required (because SNI is missing)
        to establish TLS with the client.
        """
        tssl_server = SSLTest(server_side=True)
        playbook, client_layer, tssl_client = _test_tls_client_server(tctx, sni=None)

        # We should now get instructed to open a server connection.
        data = tutils.Placeholder()
        assert (
                playbook
                >> events.DataReceived(tctx.client, tssl_client.out.read())
                << commands.OpenConnection(tctx.server)
                >> tutils.reply(None)
                << commands.Hook("tls_start", tutils.Placeholder())
                >> reply_tls_start()
                << commands.SendData(tctx.server, data)
        )

        # Establish TLS with the server...
        tssl_server.inc.write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl_server.obj.do_handshake()

        data = tutils.Placeholder()
        assert (
                playbook
                >> events.DataReceived(tctx.server, tssl_server.out.read())
                << commands.SendData(tctx.server, data)
                << commands.Hook("tls_start", tutils.Placeholder())
        )
        tssl_server.inc.write(data())
        assert tctx.server.tls_established
        # Server TLS is established, we can now reply to the client handshake...

        data = tutils.Placeholder()
        assert (
                playbook
                >> reply_tls_start()
                << commands.SendData(tctx.client, data)
        )
        tssl_client.inc.write(data())
        tssl_client.obj.do_handshake()
        interact(playbook, tctx.client, tssl_client)

        # Both handshakes completed!
        assert tctx.client.tls_established
        assert tctx.server.tls_established
        _test_echo(playbook, tssl_server, tctx.server)
        _test_echo(playbook, tssl_client, tctx.client)
