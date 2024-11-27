import pytest
from aioquic.quic.connection import QuicConnection
from aioquic.quic.connection import QuicConnectionError

from mitmproxy.proxy.layers.quic import _client_hello_parser
from mitmproxy.proxy.layers.quic._client_hello_parser import (
    quic_parse_client_hello_from_datagrams,
)
from test.mitmproxy.proxy.layers.quic.test__stream_layers import client_hello


class TestParseClientHello:
    def test_input(self):
        assert (
            quic_parse_client_hello_from_datagrams([client_hello]).sni == "example.com"
        )
        with pytest.raises(ValueError):
            quic_parse_client_hello_from_datagrams(
                [client_hello[:183] + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00"]
            )
        with pytest.raises(ValueError, match="not initial"):
            quic_parse_client_hello_from_datagrams(
                [
                    b"\\s\xd8\xd8\xa5dT\x8bc\xd3\xae\x1c\xb2\x8a7-\x1d\x19j\x85\xb0~\x8c\x80\xa5\x8cY\xac\x0ecK\x7fC2f\xbcm\x1b\xac~"
                ]
            )

    def test_invalid(self, monkeypatch):
        # XXX: This test is terrible, it should use actual invalid data.
        class InvalidClientHello(Exception):
            @property
            def data(self):
                raise EOFError()

        monkeypatch.setattr(_client_hello_parser, "QuicClientHello", InvalidClientHello)
        with pytest.raises(ValueError, match="Invalid ClientHello"):
            quic_parse_client_hello_from_datagrams([client_hello])

    def test_connection_error(self, monkeypatch):
        def raise_conn_err(self, data, addr, now):
            raise QuicConnectionError(0, 0, "Conn err")

        monkeypatch.setattr(QuicConnection, "receive_datagram", raise_conn_err)
        with pytest.raises(ValueError, match="Conn err"):
            quic_parse_client_hello_from_datagrams([client_hello])

    def test_no_return(self):
        with pytest.raises(
            ValueError, match="Invalid ClientHello packet: payload_decrypt_error"
        ):
            quic_parse_client_hello_from_datagrams(
                [client_hello[0:1200] + b"\x00" + client_hello[1200:]]
            )
