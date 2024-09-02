import ipaddress
import logging
import ssl
import time
from pathlib import Path

import pytest
from cryptography import x509
from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy import connection
from mitmproxy import options
from mitmproxy import tls
from mitmproxy.addons import tlsconfig
from mitmproxy.proxy import context
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers import quic
from mitmproxy.proxy.layers import tls as proxy_tls
from mitmproxy.test import taddons
from test.mitmproxy.proxy.layers import test_quic
from test.mitmproxy.proxy.layers import test_tls


def test_alpn_select_callback():
    ctx = SSL.Context(SSL.SSLv23_METHOD)
    conn = SSL.Connection(ctx)

    # Test that we respect addons setting `client.alpn`.
    conn.set_app_data(
        tlsconfig.AppData(server_alpn=b"h2", http2=True, client_alpn=b"qux")
    )
    assert tlsconfig.alpn_select_callback(conn, [b"http/1.1", b"qux", b"h2"]) == b"qux"
    conn.set_app_data(tlsconfig.AppData(server_alpn=b"h2", http2=True, client_alpn=b""))
    assert (
        tlsconfig.alpn_select_callback(conn, [b"http/1.1", b"qux", b"h2"])
        == SSL.NO_OVERLAPPING_PROTOCOLS
    )

    # Test that we try to mirror the server connection's ALPN
    conn.set_app_data(
        tlsconfig.AppData(server_alpn=b"h2", http2=True, client_alpn=None)
    )
    assert tlsconfig.alpn_select_callback(conn, [b"http/1.1", b"qux", b"h2"]) == b"h2"

    # Test that we respect the client's preferred HTTP ALPN.
    conn.set_app_data(tlsconfig.AppData(server_alpn=None, http2=True, client_alpn=None))
    assert (
        tlsconfig.alpn_select_callback(conn, [b"qux", b"http/1.1", b"h2"])
        == b"http/1.1"
    )
    assert tlsconfig.alpn_select_callback(conn, [b"qux", b"h2", b"http/1.1"]) == b"h2"

    # Test no overlap
    assert (
        tlsconfig.alpn_select_callback(conn, [b"qux", b"quux"])
        == SSL.NO_OVERLAPPING_PROTOCOLS
    )

    # Test that we don't select an ALPN if the server refused to select one.
    conn.set_app_data(tlsconfig.AppData(server_alpn=b"", http2=True, client_alpn=None))
    assert (
        tlsconfig.alpn_select_callback(conn, [b"http/1.1"])
        == SSL.NO_OVERLAPPING_PROTOCOLS
    )


here = Path(__file__).parent


def _ctx(opts: options.Options) -> context.Context:
    return context.Context(
        connection.Client(
            peername=("client", 1234),
            sockname=("127.0.0.1", 8080),
            timestamp_start=1605699329,
        ),
        opts,
    )


class TestTlsConfig:
    def test_configure(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            with pytest.raises(Exception, match="file does not exist"):
                tctx.configure(ta, certs=["*=nonexistent"])

            with pytest.raises(Exception, match="Invalid ECDH curve"):
                tctx.configure(ta, tls_ecdh_curve_client="invalid")

            with pytest.raises(Exception, match="Invalid certificate format"):
                tctx.configure(
                    ta,
                    certs=[
                        tdata.path(
                            "mitmproxy/net/data/verificationcerts/trusted-leaf.key"
                        )
                    ],
                )

            assert not ta.certstore.certs
            tctx.configure(
                ta,
                certs=[
                    tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")
                ],
            )
            assert ta.certstore.certs

    def test_configure_tls_version(self, caplog):
        caplog.set_level(logging.INFO)
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            for attr in [
                "tls_version_client_min",
                "tls_version_client_max",
                "tls_version_server_min",
                "tls_version_server_max",
            ]:
                caplog.clear()
                tctx.configure(ta, **{attr: "SSL3"})
                assert (
                    f"{attr} has been set to SSL3, "
                    "which is not supported by the current OpenSSL build."
                ) in caplog.text
            caplog.clear()
            tctx.configure(ta, tls_version_client_min="UNBOUNDED")
            assert (
                "tls_version_client_min has been set to UNBOUNDED. "
                "Note that your OpenSSL build only supports the following TLS versions"
            ) in caplog.text

    def test_get_cert(self, tdata):
        """Test that we generate a certificate matching the connection's context."""
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])

            ctx = _ctx(tctx.options)

            # Edge case first: We don't have _any_ idea about the server nor is there a SNI,
            # so we just return our local IP as subject.
            entry = ta.get_cert(ctx)
            assert entry.cert.cn == "127.0.0.1"

            # Here we have an existing server connection...
            ctx.server.address = ("server-address.example", 443)
            with open(
                tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.crt"),
                "rb",
            ) as f:
                ctx.server.certificate_list = [certs.Cert.from_pem(f.read())]
            entry = ta.get_cert(ctx)
            assert entry.cert.cn == "example.mitmproxy.org"
            assert entry.cert.altnames == x509.GeneralNames(
                [
                    x509.DNSName("example.mitmproxy.org"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.DNSName("server-address.example"),
                ]
            )

            # And now we also incorporate SNI.
            ctx.client.sni = "🌈.sni.example"
            entry = ta.get_cert(ctx)
            assert entry.cert.altnames == x509.GeneralNames(
                [
                    x509.DNSName("example.mitmproxy.org"),
                    x509.DNSName("xn--og8h.sni.example"),
                    x509.DNSName("server-address.example"),
                ]
            )

            with open(tdata.path("mitmproxy/data/invalid-subject.pem"), "rb") as f:
                ctx.server.certificate_list = [certs.Cert.from_pem(f.read())]
            with pytest.warns(UserWarning):
                assert ta.get_cert(ctx)  # does not raise

    def test_tls_clienthello(self):
        # only really testing for coverage here, there's no point in mirroring the individual conditions
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ch = tls.ClientHelloData(ctx, None)  # type: ignore
            ta.tls_clienthello(ch)
            assert not ch.establish_server_tls_first

    def do_handshake(
        self,
        tssl_client: test_tls.SSLTest | SSL.Connection,
        tssl_server: test_tls.SSLTest | SSL.Connection,
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

    def quic_do_handshake(
        self,
        tssl_client: test_quic.SSLTest,
        tssl_server: test_quic.SSLTest,
    ) -> bool:
        tssl_server.write(tssl_client.read())
        tssl_client.write(tssl_server.read())
        tssl_server.write(tssl_client.read())
        return tssl_client.handshake_completed() and tssl_server.handshake_completed()

    def test_tls_start_client(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])
            tctx.configure(
                ta,
                certs=[
                    tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")
                ],
                ciphers_client="ECDHE-ECDSA-AES128-GCM-SHA256",
            )
            ctx = _ctx(tctx.options)

            tls_start = tls.TlsData(ctx.client, context=ctx)
            ta.tls_start_client(tls_start)
            tssl_server = tls_start.ssl_conn

            # assert that a preexisting ssl_conn is not overwritten
            ta.tls_start_client(tls_start)
            assert tssl_server is tls_start.ssl_conn

            tssl_client = test_tls.SSLTest()
            assert self.do_handshake(tssl_client, tssl_server)
            assert tssl_client.obj.getpeercert()["subjectAltName"] == (
                ("DNS", "example.mitmproxy.org"),
            )

    def test_quic_start_client(self, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ta.configure(["confdir"])
            tctx.configure(
                ta,
                certs=[
                    tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")
                ],
                ciphers_client="CHACHA20_POLY1305_SHA256",
            )
            ctx = _ctx(tctx.options)

            tls_start = quic.QuicTlsData(ctx.client, context=ctx)
            ta.quic_start_client(tls_start)
            settings_server = tls_start.settings
            settings_server.alpn_protocols = ["h3"]
            tssl_server = test_quic.SSLTest(server_side=True, settings=settings_server)

            # assert that a preexisting settings is not overwritten
            ta.quic_start_client(tls_start)
            assert settings_server is tls_start.settings

            tssl_client = test_quic.SSLTest(alpn=["h3"])
            assert self.quic_do_handshake(tssl_client, tssl_server)
            san = tssl_client.quic.tls._peer_certificate.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            )
            assert san.value.get_values_for_type(x509.DNSName) == [
                "example.mitmproxy.org"
            ]

    def test_tls_start_server_cannot_verify(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            ctx.server.sni = ""  # explicitly opt out of using the address.

            tls_start = tls.TlsData(ctx.server, context=ctx)
            with pytest.raises(
                ValueError, match="Cannot validate certificate hostname without SNI"
            ):
                ta.tls_start_server(tls_start)

    def test_tls_start_server_verify_failed(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.client.alpn_offers = [b"h2"]
            ctx.client.cipher_list = ["TLS_AES_256_GCM_SHA384", "ECDHE-RSA-AES128-SHA"]
            ctx.server.address = ("example.mitmproxy.org", 443)

            tls_start = tls.TlsData(ctx.server, context=ctx)
            ta.tls_start_server(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)
            with pytest.raises(SSL.Error, match="certificate verify failed"):
                assert self.do_handshake(tssl_client, tssl_server)

    @pytest.mark.parametrize("hostname", ["example.mitmproxy.org", "192.0.2.42"])
    def test_tls_start_server_verify_ok(self, hostname, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = (hostname, 443)
            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

            tls_start = tls.TlsData(ctx.server, context=ctx)
            ta.tls_start_server(tls_start)
            tssl_client = tls_start.ssl_conn

            # assert that a preexisting ssl_conn is not overwritten
            ta.tls_start_server(tls_start)
            assert tssl_client is tls_start.ssl_conn

            tssl_server = test_tls.SSLTest(server_side=True, sni=hostname.encode())
            assert self.do_handshake(tssl_client, tssl_server)

    @pytest.mark.parametrize("hostname", ["example.mitmproxy.org", "192.0.2.42"])
    def test_quic_start_server_verify_ok(self, hostname, tdata):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = (hostname, 443)
            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

            tls_start = quic.QuicTlsData(ctx.server, context=ctx)
            ta.quic_start_server(tls_start)
            settings_client = tls_start.settings
            settings_client.alpn_protocols = ["h3"]
            tssl_client = test_quic.SSLTest(settings=settings_client)

            # assert that a preexisting ssl_conn is not overwritten
            ta.quic_start_server(tls_start)
            assert settings_client is tls_start.settings

            tssl_server = test_quic.SSLTest(
                server_side=True, sni=hostname.encode(), alpn=["h3"]
            )
            assert self.quic_do_handshake(tssl_client, tssl_server)

    def test_tls_start_server_insecure(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)

            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=None,
                ssl_insecure=True,
                http2=False,
                ciphers_server="ALL",
            )
            tls_start = tls.TlsData(ctx.server, context=ctx)
            ta.tls_start_server(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)
            assert self.do_handshake(tssl_client, tssl_server)

    def test_quic_start_server_insecure(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            ctx.client.alpn_offers = [b"h3"]

            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=None,
                ssl_insecure=True,
                ciphers_server="CHACHA20_POLY1305_SHA256",
            )
            tls_start = quic.QuicTlsData(ctx.server, context=ctx)
            ta.quic_start_server(tls_start)
            tssl_client = test_quic.SSLTest(settings=tls_start.settings)
            tssl_server = test_quic.SSLTest(server_side=True, alpn=["h3"])
            assert self.quic_do_handshake(tssl_client, tssl_server)

    def test_alpn_selection(self):
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            ctx = _ctx(tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            tls_start = tls.TlsData(ctx.server, context=ctx)

            def assert_alpn(http2, client_offers, expected):
                tctx.configure(ta, http2=http2)
                ctx.client.alpn_offers = client_offers
                ctx.server.alpn_offers = None
                tls_start.ssl_conn = None
                ta.tls_start_server(tls_start)
                assert ctx.server.alpn_offers == expected

            assert_alpn(
                True,
                (proxy_tls.HTTP2_ALPN, *proxy_tls.HTTP1_ALPNS, b"foo"),
                (proxy_tls.HTTP2_ALPN, *proxy_tls.HTTP1_ALPNS, b"foo"),
            )
            assert_alpn(
                False,
                (proxy_tls.HTTP2_ALPN, *proxy_tls.HTTP1_ALPNS, b"foo"),
                (*proxy_tls.HTTP1_ALPNS, b"foo"),
            )
            assert_alpn(True, [], [])
            assert_alpn(False, [], [])
            ctx.client.timestamp_tls_setup = time.time()
            # make sure that we don't upgrade h1 to h2,
            # see comment in tlsconfig.py
            assert_alpn(True, [], [])

    def test_no_h2_proxy(self, tdata):
        """Do not negotiate h2 on the client<->proxy connection in secure web proxy mode,
        https://github.com/mitmproxy/mitmproxy/issues/4689"""

        ta = tlsconfig.TlsConfig()
        with taddons.context(ta) as tctx:
            tctx.configure(
                ta,
                certs=[
                    tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.pem")
                ],
            )

            ctx = _ctx(tctx.options)
            # mock up something that looks like a secure web proxy.
            ctx.layers = [modes.HttpProxy(ctx), 123]
            tls_start = tls.TlsData(ctx.client, context=ctx)
            ta.tls_start_client(tls_start)
            assert tls_start.ssl_conn.get_app_data()["client_alpn"] == b"http/1.1"

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
            ctx = _ctx(tctx.options)
            ctx.server.address = ("example.mitmproxy.org", 443)
            tctx.configure(
                ta,
                client_certs=tdata.path(client_certs),
                ssl_verify_upstream_trusted_ca=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

            tls_start = tls.TlsData(ctx.server, context=ctx)
            ta.tls_start_server(tls_start)
            tssl_client = tls_start.ssl_conn
            tssl_server = test_tls.SSLTest(server_side=True)

            assert self.do_handshake(tssl_client, tssl_server)
            assert tssl_server.obj.getpeercert()

    async def test_ca_expired(self, monkeypatch, caplog):
        monkeypatch.setattr(certs.Cert, "has_expired", lambda self: True)
        ta = tlsconfig.TlsConfig()
        with taddons.context(ta):
            ta.configure(["confdir"])
            assert "The mitmproxy certificate authority has expired" in caplog.text
