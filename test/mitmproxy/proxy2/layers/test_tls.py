import os
import ssl
import typing

import pytest

from mitmproxy.proxy2 import context, events, commands
from mitmproxy.proxy2.layers import tls
from test.mitmproxy.proxy2 import tutils


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
    with pytest.raises(ValueError, msg="Expected TLS record"):
        next(tls.handshake_record_contents(b"GET /error"))

    empty_record = bytes.fromhex("1603010000")
    with pytest.raises(ValueError, msg="Record must not be empty"):
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

    def __init__(self, server_side=False, alpn=None):
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
            server_hostname=None if server_side else "example.com",
            server_side=server_side,
        )


def _test_tls_client_server(
    tctx: context.Context,
    alpn: typing.Optional[str]
) -> typing.Tuple[tutils.playbook[tls.ClientTLSLayer], SSLTest]:
    layer = tls.ClientTLSLayer(tctx)
    playbook = tutils.playbook(layer)
    tctx.server.tls = True
    tctx.server.address = ("example.com", 443)
    tssl_client = SSLTest(alpn=alpn)

    # Handshake
    assert (
        playbook
        << None
    )

    with pytest.raises(ssl.SSLWantReadError):
        tssl_client.obj.do_handshake()
    client_hello = tssl_client.out.read()
    assert (
        playbook
        >> events.DataReceived(tctx.client, client_hello[:42])
        << None
    )
    # Still waiting...
    # Finish sending ClientHello
    playbook >> events.DataReceived(tctx.client, client_hello[42:])
    return playbook, tssl_client


def echo(playbook: tutils.playbook, tssl: SSLTest, conn: context.Connection) -> None:
    tssl.obj.write(b"Hello World")
    data = tutils.Placeholder()
    assert (
        playbook
        >> events.DataReceived(conn, tssl.out.read())
        << commands.Hook("next_layer", tutils.Placeholder())
        >> tutils.next_layer(tutils.EchoLayer)
        << commands.SendData(conn, data)
    )
    tssl.inc.write(data())
    assert tssl.obj.read() == b"hello world"


class TestServerTLS:
    def test_no_tls(self, tctx: context.Context):
        """Test TLS layer without TLS"""
        layer = tls.ServerTLSLayer(tctx)
        playbook = tutils.playbook(layer)

        # Handshake
        assert (
            playbook
            >> events.DataReceived(tctx.client, b"Hello World")
            << commands.Hook("next_layer", tutils.Placeholder())
            >> tutils.next_layer(tutils.EchoLayer)
            << commands.SendData(tctx.client, b"hello world")
        )

    def test_no_connection(self, tctx):
        """
        The server TLS layer is initiated, but there is no active connection yet, so nothing
        should be done.
        """
        layer = tls.ServerTLSLayer(tctx)
        playbook = tutils.playbook(layer)
        tctx.server.tls = True

        # We did not have a server connection before, so let's do nothing.
        assert (
            playbook
            << None
        )

    def test_simple(self, tctx):
        layer = tls.ServerTLSLayer(tctx)
        playbook = tutils.playbook(layer)
        tctx.server.connected = True
        tctx.server.address = ("example.com", 443)
        tctx.server.tls = True

        tssl = SSLTest(server_side=True)

        # send ClientHello
        data = tutils.Placeholder()
        assert (
            playbook
            << commands.SendData(tctx.server, data)
        )

        # receive ServerHello, finish client handshake
        tssl.inc.write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl.obj.do_handshake()
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl.out.read())
            << commands.SendData(tctx.server, data)
        )
        tssl.inc.write(data())

        # finish server handshake
        tssl.obj.do_handshake()
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl.out.read())
            << None
        )

        assert tctx.server.tls_established
        assert tctx.server.sni == b"example.com"

        # Echo
        echo(playbook, tssl, tctx.server)


class TestClientTLS:
    def test_simple(self, tctx: context.Context):
        """Test TLS with client only"""
        layer = tls.ClientTLSLayer(tctx)
        playbook = tutils.playbook(layer)
        tssl = SSLTest()

        # Handshake
        assert playbook
        assert layer._handle_event == layer.state_wait_for_clienthello

        def interact():
            data = tutils.Placeholder()
            assert (
                playbook
                >> events.DataReceived(tctx.client, tssl.out.read())
                << commands.SendData(tctx.client, data)
            )
            tssl.inc.write(data())
            try:
                tssl.obj.do_handshake()
            except ssl.SSLWantReadError:
                return False
            else:
                return True

        # receive ClientHello, send ServerHello
        with pytest.raises(ssl.SSLWantReadError):
            tssl.obj.do_handshake()
        assert not interact()
        # Finish Handshake
        assert interact()
        tssl.obj.do_handshake()

        assert layer._handle_event == layer.state_process

        # Echo
        echo(playbook, tssl, tctx.client)
        assert (
            playbook
            >> events.DataReceived(tctx.server, b"Hello")
            << commands.SendData(tctx.server, b"hello")
        )

    def test_no_server_conn_required(self, tctx):
        """
        Here we test the scenario where a server connection is _not_ required
        to establish TLS with the client. After determining this when parsing the ClientHello,
        we only establish a connection with the client. The server connection may ultimately
        be established when OpenConnection is called.
        """
        playbook, _ = _test_tls_client_server(tctx, None)
        data = tutils.Placeholder()
        assert (
            playbook
            << commands.SendData(tctx.client, data)
        )
        assert data()
        assert playbook.layer._handle_event == playbook.layer.state_process

    def test_alpn(self, tctx):
        """
        Here we test the scenario where a server connection is required (e.g. because of ALPN negotation)
        to establish TLS with the client.
        """
        tssl_server = SSLTest(server_side=True, alpn=["foo", "bar"])

        playbook, tssl_client = _test_tls_client_server(tctx, ["qux", "foo"])

        # We should now get instructed to open a server connection.
        assert (
            playbook
            << commands.OpenConnection(tctx.server)
        )
        tctx.server.connected = True
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.OpenConnectionReply(-1, None)
            << commands.SendData(tctx.server, data)
        )
        assert playbook.layer._handle_event == playbook.layer.state_wait_for_server_tls
        assert playbook.layer.child_layer.tls[tctx.server]

        # Establish TLS with the server...
        tssl_server.inc.write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl_server.obj.do_handshake()
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl_server.out.read())
            << commands.SendData(tctx.server, data)
        )
        tssl_server.inc.write(data())
        tssl_server.obj.do_handshake()
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl_server.out.read())
            << commands.SendData(tctx.client, data)
        )

        assert playbook.layer._handle_event == playbook.layer.state_process
        assert tctx.server.tls_established

        # Server TLS is established, we can now reply to the client handshake...
        tssl_client.inc.write(data())
        with pytest.raises(ssl.SSLWantReadError):
            tssl_client.obj.do_handshake()
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.out.read())
            << commands.SendData(tctx.client, data)
        )
        tssl_client.inc.write(data())
        tssl_client.obj.do_handshake()

        # Both handshakes completed!
        assert tctx.client.tls_established
        assert tctx.server.tls_established

        assert tssl_client.obj.selected_alpn_protocol() == "foo"
        assert tssl_server.obj.selected_alpn_protocol() == "foo"
