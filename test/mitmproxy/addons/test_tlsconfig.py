import ssl
import time
from pathlib import Path
from typing import Union

import pytest

from OpenSSL import SSL
from mitmproxy import certs
from mitmproxy.addons import tlsconfig
from mitmproxy.proxy import context
from mitmproxy.proxy.layers import tls
from mitmproxy.test import taddons
from test.mitmproxy.proxy.layers import test_tls


def test_alpn_select_callback():
    ctx = SSL.Context(SSL.SSLv23_METHOD)
    conn = SSL.Connection(ctx)
    conn.set_app_data(tlsconfig.AppData(server_alpn=b"h2", http2=True))

    # Test that we try to mirror the server connection's ALPN
    assert tlsconfig.alpn_select_callback(conn, [b"http/1.1", b"qux", b"h2"]) == b"h2"

    # Test that we respect the client's preferred HTTP ALPN.
    conn.set_app_data(tlsconfig.AppData(server_alpn=None, http2=True))
    assert tlsconfig.alpn_select_callback(conn, [b"qux", b"http/1.1", b"h2"]) == b"http/1.1"
    assert tlsconfig.alpn_select_callback(conn, [b"qux", b"h2", b"http/1.1"]) == b"h2"

    # Test no overlap
    assert tlsconfig.alpn_select_callback(conn, [b"qux", b"quux"]) == SSL.NO_OVERLAPPING_PROTOCOLS


here = Path(__file__).parent


class TestTlsConfig:
    def test_configure(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            with pytest.raises(Exception, match="file does not exist"):
                tctx.configure(ta, certs=["*=nonexistent"])

            with pytest.raises(Exception, match="Invalid certificate format"):
                tctx.configure(ta, certs=[tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.key")])

            assert not ta.certstore.certs
            tctx.configure(ta, certs=[tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")])
            assert ta.certstore.certs

    def test_get_cert(self, tdata):
        """Test that we generate a certificate matching the connection's context."""
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])

            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)

            # Edge case first: We don't have _any_ idea about the server, so we just return "mitmproxy" as subject.
            entry = ta.get_cert(ctx)
            assert entry.cert.cn == "mitmproxy"

            # Here we have an existing server connection...
            ctx.server.address = ("server-address.example", 443)
            with open(tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.crt"), "rb") as f:
                ctx.server.certificate_list = [certs.Cert.from_pem(f.read())]
            entry = ta.get_cert(ctx)
            assert entry.cert.cn == "example.mitmproxy.org"
            assert entry.cert.altnames == ["example.mitmproxy.org", "server-address.example"]

            # And now we also incorporate SNI.
            ctx.client.sni = "sni.example"
            entry = ta.get_cert(ctx)
            assert entry.cert.altnames == ["example.mitmproxy.org", "sni.example"]

    def test_tls_clienthello(self):
        # only really testing for coverage here, there's no point in mirroring the individual conditions
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ch = tls.ClientHelloData(ctx)
            ta.tls_clienthello(ch)
            assert not ch.establish_server_tls_first

    def do_handshake(
            self,
            tssl_client: Union[test_tls.SSLTest, SSL.Connection],
            tssl_server: Union[test_tls.SSLTest, SSL.Connection]
    ) -> bool:
        # ClientHello
        with pytest.raises((ssl.SSLWantReadError, SSL.WantReadError)):
            tssl_client.do_handshake()
        tssl_server.bio_write(tssl_client.bio_read(65536))

        # ServerHello
        with pytest.raises((ssl.SSLWantReadError, SSL.WantReadError)):
            tssl_server.do_handshake()
        tssl_client.bio_write(tssl_server.bio_read(65536))

        # done
        tssl_client.do_handshake()
        tssl_server.bio_write(tssl_client.bio_read(65536))
        tssl_server.do_handshake()

        return True

    def test_create_client_proxy_ssl_conn(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])
            tctx.configure(
                ta,
                certs=[tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")],
                ciphers_client="ECDHE-ECDSA-AES128-GCM-SHA256",
            )
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)

            tls_start = tls.TlsStartData(ctx.client, context=ctx)
            ta.tls_start(tls_start)
            tssl_server = tls_start.ssl_conn
            tssl_client = test_tls.SSLTest()
            assert self.do_handshake(tssl_client, tssl_server)
            assert tssl_client.obj.getpeercert()["subjectAltName"] == (("DNS", "example.mitmproxy.org"),)

    def test_create_proxy_server_ssl_conn_verify_failed(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ctx.client.alpn_offers = [b"h2"]
            ctx.client.cipher_list = ["TLS_AES_256_GCM_SHA384", "ECDHE-RSA-AES128-SHA"]
            ctx.server.address = ("example.mitmproxy.org", 443)

            tls_start = tls.TlsStartData(ctx.server, context=ctx)
            ta.tls_start(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)
            with pytest.raises(SSL.Error, match="certificate verify failed"):
                assert self.do_handshake(tssl_client, tssl_server)

    def test_create_proxy_server_ssl_conn_verify_ok(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            tctx.configure(ta, ssl_verify_upstream_trusted_ca=tdata.path(
                "mitmproxy/net/data/verificationcerts/trusted-root.crt"))

            tls_start = tls.TlsStartData(ctx.server, context=ctx)
            ta.tls_start(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)
            assert self.do_handshake(tssl_client, tssl_server)

    def test_create_proxy_server_ssl_conn_insecure(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)

            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=None,
                ssl_insecure=True,
                http2=False,
                ciphers_server="ALL"
            )
            tls_start = tls.TlsStartData(ctx.server, context=ctx)
            ta.tls_start(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)
            assert self.do_handshake(tssl_client, tssl_server)

    def test_alpn_selection(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            tls_start = tls.TlsStartData(ctx.server, context=ctx)

            def assert_alpn(http2, client_offers, expected):
                tctx.configure(ta, http2=http2)
                ctx.client.alpn_offers = client_offers
                ctx.server.alpn_offers = None
                ta.tls_start(tls_start)
                assert ctx.server.alpn_offers == expected

            assert_alpn(True, tls.HTTP_ALPNS + (b"foo",), tls.HTTP_ALPNS + (b"foo",))
            assert_alpn(False, tls.HTTP_ALPNS + (b"foo",), tls.HTTP1_ALPNS + (b"foo",))
            assert_alpn(True, [], tls.HTTP_ALPNS)
            assert_alpn(False, [], tls.HTTP1_ALPNS)
            ctx.client.timestamp_tls_setup = time.time()
            # make sure that we don't upgrade h1 to h2,
            # see comment in tlsconfig.py
            assert_alpn(True, [], [])

    @pytest.mark.parametrize(
        "client_certs",
        [
            "mitmproxy/net/data/verificationcerts/trusted-leaf.pem",
            "mitmproxy/net/data/verificationcerts/",
        ],
    )
    def test_client_cert_file(self, tdata, client_certs):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            tctx.configure(
                ta,
                client_certs=tdata.path(client_certs),
                ssl_verify_upstream_trusted_ca=tdata.path("mitmproxy/net/data/verificationcerts/trusted-root.crt"),
            )

            tls_start = tls.TlsStartData(ctx.server, context=ctx)
            ta.tls_start(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)

            assert self.do_handshake(tssl_client, tssl_server)
            assert tssl_server.obj.getpeercert()

    @pytest.mark.asyncio
    async def test_ca_expired(self, monkeypatch):
        monkeypatch.setattr(certs.Cert, "has_expired", lambda self: True)
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])
            await tctx.master.await_log("The mitmproxy certificate authority has expired", "warn")
