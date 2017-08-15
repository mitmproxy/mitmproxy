import ssl

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
    def __init__(self):
        self.inc = ssl.MemoryBIO()
        self.out = ssl.MemoryBIO()
        self.ctx = ssl.SSLContext()
        self.obj = self.ctx.wrap_bio(self.inc, self.out, server_side=False)
        try:
            self.obj.do_handshake()
        except ssl.SSLWantReadError:
            pass


def test_client_tls(tctx: context.Context):
    """Test TLS with client only"""
    layer = tls.TLSLayer(tctx)
    playbook = tutils.playbook(layer)
    tctx.client.tls = True
    tssl = SSLTest()

    # Handshake
    assert playbook
    assert layer.state[tctx.client] == tls.ConnectionState.NEGOTIATING
    assert layer.state[tctx.server] == tls.ConnectionState.NO_TLS

    def interact():
        data = tutils.Placeholder()
        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl.out.read())
            << commands.SendData(tctx.client, data)
        )
        tssl.inc.write(data())

    # Send ClientHello, receive ServerHello
    interact()
    with pytest.raises(ssl.SSLWantReadError):
        tssl.obj.do_handshake()
    # Finish Handshake
    interact()
    tssl.obj.do_handshake()

    assert layer.state[tctx.client] == tls.ConnectionState.ESTABLISHED
    assert layer.state[tctx.server] == tls.ConnectionState.NO_TLS

    # Echo
    tssl.obj.write(b"Hello World")
    nextl = tutils.Placeholder()
    assert (
        playbook
        >> events.DataReceived(tctx.client, tssl.out.read())
        << commands.Log(
            "PlainDataReceived(client, b'Hello World')")
        << commands.Hook("next_layer", nextl)
    )
    nextl().layer = tutils.EchoLayer(nextl().context)
    data = tutils.Placeholder()
    assert (
        playbook
        >> events.HookReply(-1, None)
        << commands.Log("PlainSendData(client, b'hello world')")
        << commands.SendData(tctx.client, data)
    )
    tssl.inc.write(data())
    assert tssl.obj.read() == b"hello world"
