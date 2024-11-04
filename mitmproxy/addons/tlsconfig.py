import ipaddress
import logging
import os
import ssl
from pathlib import Path
from typing import Any
from typing import TypedDict

from aioquic.h3.connection import H3_ALPN
from aioquic.tls import CipherSuite
from cryptography import x509
from OpenSSL import crypto
from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import tls
from mitmproxy.net import tls as net_tls
from mitmproxy.options import CONF_BASENAME
from mitmproxy.proxy import context
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers import quic
from mitmproxy.proxy.layers import tls as proxy_tls

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://ssl-config.mozilla.org/#config=old

DEFAULT_CIPHERS = (
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "DHE-RSA-AES128-GCM-SHA256",
    "DHE-RSA-AES256-GCM-SHA384",
    "DHE-RSA-CHACHA20-POLY1305",
    "ECDHE-ECDSA-AES128-SHA256",
    "ECDHE-RSA-AES128-SHA256",
    "ECDHE-ECDSA-AES128-SHA",
    "ECDHE-RSA-AES128-SHA",
    "ECDHE-ECDSA-AES256-SHA384",
    "ECDHE-RSA-AES256-SHA384",
    "ECDHE-ECDSA-AES256-SHA",
    "ECDHE-RSA-AES256-SHA",
    "DHE-RSA-AES128-SHA256",
    "DHE-RSA-AES256-SHA256",
    "AES128-GCM-SHA256",
    "AES256-GCM-SHA384",
    "AES128-SHA256",
    "AES256-SHA256",
    "AES128-SHA",
    "AES256-SHA",
    "DES-CBC3-SHA",
)

# 2022/05: X509_CHECK_FLAG_NEVER_CHECK_SUBJECT is not available in LibreSSL, ignore gracefully as it's not critical.
DEFAULT_HOSTFLAGS = (
    SSL._lib.X509_CHECK_FLAG_NO_PARTIAL_WILDCARDS  # type: ignore
    | getattr(SSL._lib, "X509_CHECK_FLAG_NEVER_CHECK_SUBJECT", 0)  # type: ignore
)


class AppData(TypedDict):
    client_alpn: bytes | None
    server_alpn: bytes | None
    http2: bool


def alpn_select_callback(conn: SSL.Connection, options: list[bytes]) -> Any:
    app_data: AppData = conn.get_app_data()
    client_alpn = app_data["client_alpn"]
    server_alpn = app_data["server_alpn"]
    http2 = app_data["http2"]
    if client_alpn is not None:
        if client_alpn in options:
            return client_alpn
        else:
            return SSL.NO_OVERLAPPING_PROTOCOLS
    if server_alpn and server_alpn in options:
        return server_alpn
    if server_alpn == b"":
        # We do have a server connection, but the remote server refused to negotiate a protocol:
        # We need to mirror this on the client connection.
        return SSL.NO_OVERLAPPING_PROTOCOLS
    http_alpns = proxy_tls.HTTP_ALPNS if http2 else proxy_tls.HTTP1_ALPNS
    # client sends in order of preference, so we are nice and respect that.
    for alpn in options:
        if alpn in http_alpns:
            return alpn
    else:
        return SSL.NO_OVERLAPPING_PROTOCOLS


class TlsConfig:
    """
    This addon supplies the proxy core with the desired OpenSSL connection objects to negotiate TLS.
    """

    certstore: certs.CertStore = None  # type: ignore

    # TODO: We should support configuring TLS 1.3 cipher suites (https://github.com/mitmproxy/mitmproxy/issues/4260)
    # TODO: We should re-use SSL.Context options here, if only for TLS session resumption.
    #       This may require patches to pyOpenSSL, as some functionality is only exposed on contexts.
    # TODO: This addon should manage the following options itself, which are current defined in mitmproxy/options.py:
    #  - upstream_cert
    #  - add_upstream_certs_to_client_chain
    #  - ciphers_client
    #  - ciphers_server
    #  - key_size
    #  - certs
    #  - cert_passphrase
    #  - ssl_verify_upstream_trusted_ca
    #  - ssl_verify_upstream_trusted_confdir

    def load(self, loader):
        loader.add_option(
            name="tls_version_client_min",
            typespec=str,
            default=net_tls.DEFAULT_MIN_VERSION.name,
            choices=[x.name for x in net_tls.Version],
            help=f"Set the minimum TLS version for client connections.",
        )
        loader.add_option(
            name="tls_version_client_max",
            typespec=str,
            default=net_tls.DEFAULT_MAX_VERSION.name,
            choices=[x.name for x in net_tls.Version],
            help=f"Set the maximum TLS version for client connections.",
        )
        loader.add_option(
            name="tls_version_server_min",
            typespec=str,
            default=net_tls.DEFAULT_MIN_VERSION.name,
            choices=[x.name for x in net_tls.Version],
            help=f"Set the minimum TLS version for server connections.",
        )
        loader.add_option(
            name="tls_version_server_max",
            typespec=str,
            default=net_tls.DEFAULT_MAX_VERSION.name,
            choices=[x.name for x in net_tls.Version],
            help=f"Set the maximum TLS version for server connections.",
        )
        loader.add_option(
            name="tls_ecdh_curve_client",
            typespec=str | None,
            default=None,
            help="Use a specific elliptic curve for ECDHE key exchange on client connections. "
            'OpenSSL syntax, for example "prime256v1" (see `openssl ecparam -list_curves`).',
        )
        loader.add_option(
            name="tls_ecdh_curve_server",
            typespec=str | None,
            default=None,
            help="Use a specific elliptic curve for ECDHE key exchange on server connections. "
            'OpenSSL syntax, for example "prime256v1" (see `openssl ecparam -list_curves`).',
        )

    def tls_clienthello(self, tls_clienthello: tls.ClientHelloData):
        conn_context = tls_clienthello.context
        tls_clienthello.establish_server_tls_first = (
            conn_context.server.tls and ctx.options.connection_strategy == "eager"
        )

    def tls_start_client(self, tls_start: tls.TlsData) -> None:
        """Establish TLS or DTLS between client and proxy."""
        if tls_start.ssl_conn is not None:
            return  # a user addon has already provided the pyOpenSSL context.

        assert isinstance(tls_start.conn, connection.Client)

        client: connection.Client = tls_start.conn
        server: connection.Server = tls_start.context.server

        entry = self.get_cert(tls_start.context)

        if not client.cipher_list and ctx.options.ciphers_client:
            client.cipher_list = ctx.options.ciphers_client.split(":")
        # don't assign to client.cipher_list, doesn't need to be stored.
        cipher_list = client.cipher_list or DEFAULT_CIPHERS

        if ctx.options.add_upstream_certs_to_client_chain:  # pragma: no cover
            # exempted from coverage until https://bugs.python.org/issue18233 is fixed.
            extra_chain_certs = server.certificate_list
        else:
            extra_chain_certs = []

        ssl_ctx = net_tls.create_client_proxy_context(
            method=net_tls.Method.DTLS_SERVER_METHOD
            if tls_start.is_dtls
            else net_tls.Method.TLS_SERVER_METHOD,
            min_version=net_tls.Version[ctx.options.tls_version_client_min],
            max_version=net_tls.Version[ctx.options.tls_version_client_max],
            cipher_list=tuple(cipher_list),
            ecdh_curve=ctx.options.tls_ecdh_curve_client,
            chain_file=entry.chain_file,
            request_client_cert=False,
            alpn_select_callback=alpn_select_callback,
            extra_chain_certs=tuple(extra_chain_certs),
            dhparams=self.certstore.dhparams,
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)

        tls_start.ssl_conn.use_certificate(entry.cert.to_pyopenssl())
        tls_start.ssl_conn.use_privatekey(
            crypto.PKey.from_cryptography_key(entry.privatekey)
        )

        # Force HTTP/1 for secure web proxies, we currently don't support CONNECT over HTTP/2.
        # There is a proof-of-concept branch at https://github.com/mhils/mitmproxy/tree/http2-proxy,
        # but the complexity outweighs the benefits for now.
        if len(tls_start.context.layers) == 2 and isinstance(
            tls_start.context.layers[0], modes.HttpProxy
        ):
            client_alpn: bytes | None = b"http/1.1"
        else:
            client_alpn = client.alpn

        tls_start.ssl_conn.set_app_data(
            AppData(
                client_alpn=client_alpn,
                server_alpn=server.alpn,
                http2=ctx.options.http2,
            )
        )
        tls_start.ssl_conn.set_accept_state()

    def tls_start_server(self, tls_start: tls.TlsData) -> None:
        """Establish TLS or DTLS between proxy and server."""
        if tls_start.ssl_conn is not None:
            return  # a user addon has already provided the pyOpenSSL context.

        assert isinstance(tls_start.conn, connection.Server)

        client: connection.Client = tls_start.context.client
        # tls_start.conn may be different from tls_start.context.server, e.g. an upstream HTTPS proxy.
        server: connection.Server = tls_start.conn
        assert server.address

        if ctx.options.ssl_insecure:
            verify = net_tls.Verify.VERIFY_NONE
        else:
            verify = net_tls.Verify.VERIFY_PEER

        if server.sni is None:
            server.sni = client.sni or server.address[0]

        if not server.alpn_offers:
            if client.alpn_offers:
                if ctx.options.http2:
                    # We would perfectly support HTTP/1 -> HTTP/2, but we want to keep things on the same protocol
                    # version. There are some edge cases where we want to mirror the regular server's behavior
                    # accurately, for example header capitalization.
                    server.alpn_offers = tuple(client.alpn_offers)
                else:
                    server.alpn_offers = tuple(
                        x for x in client.alpn_offers if x != b"h2"
                    )
            else:
                # We either have no client TLS or a client without ALPN.
                # - If the client does use TLS but did not send an ALPN extension, we want to mirror that upstream.
                # - If the client does not use TLS, there's no clear-cut answer. As a pragmatic approach, we also do
                #   not send any ALPN extension in this case, which defaults to whatever protocol we are speaking
                #   or falls back to HTTP.
                server.alpn_offers = []

        if not server.cipher_list and ctx.options.ciphers_server:
            server.cipher_list = ctx.options.ciphers_server.split(":")
        # don't assign to client.cipher_list, doesn't need to be stored.
        cipher_list = server.cipher_list or DEFAULT_CIPHERS

        client_cert: str | None = None
        if ctx.options.client_certs:
            client_certs = os.path.expanduser(ctx.options.client_certs)
            if os.path.isfile(client_certs):
                client_cert = client_certs
            else:
                server_name: str = server.sni or server.address[0]
                p = os.path.join(client_certs, f"{server_name}.pem")
                if os.path.isfile(p):
                    client_cert = p

        ssl_ctx = net_tls.create_proxy_server_context(
            method=net_tls.Method.DTLS_CLIENT_METHOD
            if tls_start.is_dtls
            else net_tls.Method.TLS_CLIENT_METHOD,
            min_version=net_tls.Version[ctx.options.tls_version_server_min],
            max_version=net_tls.Version[ctx.options.tls_version_server_max],
            cipher_list=tuple(cipher_list),
            ecdh_curve=ctx.options.tls_ecdh_curve_server,
            verify=verify,
            ca_path=ctx.options.ssl_verify_upstream_trusted_confdir,
            ca_pemfile=ctx.options.ssl_verify_upstream_trusted_ca,
            client_cert=client_cert,
            legacy_server_connect=ctx.options.ssl_insecure,
        )

        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        if server.sni:
            # We need to set SNI + enable hostname verification.
            assert isinstance(server.sni, str)
            # Manually enable hostname verification on the context object.
            # https://wiki.openssl.org/index.php/Hostname_validation
            param = SSL._lib.SSL_get0_param(tls_start.ssl_conn._ssl)  # type: ignore
            # Matching on the CN is disabled in both Chrome and Firefox, so we disable it, too.
            # https://www.chromestatus.com/feature/4981025180483584

            SSL._lib.X509_VERIFY_PARAM_set_hostflags(param, DEFAULT_HOSTFLAGS)  # type: ignore

            try:
                ip: bytes = ipaddress.ip_address(server.sni).packed
            except ValueError:
                host_name = server.sni.encode("idna")
                tls_start.ssl_conn.set_tlsext_host_name(host_name)
                ok = SSL._lib.X509_VERIFY_PARAM_set1_host(  # type: ignore
                    param, host_name, len(host_name)
                )  # type: ignore
                SSL._openssl_assert(ok == 1)  # type: ignore
            else:
                # RFC 6066: Literal IPv4 and IPv6 addresses are not permitted in "HostName",
                # so we don't call set_tlsext_host_name.
                ok = SSL._lib.X509_VERIFY_PARAM_set1_ip(param, ip, len(ip))  # type: ignore
                SSL._openssl_assert(ok == 1)  # type: ignore
        elif verify is not net_tls.Verify.VERIFY_NONE:
            raise ValueError("Cannot validate certificate hostname without SNI")

        if server.alpn_offers:
            tls_start.ssl_conn.set_alpn_protos(server.alpn_offers)

        tls_start.ssl_conn.set_connect_state()

    def quic_start_client(self, tls_start: quic.QuicTlsData) -> None:
        """Establish QUIC between client and proxy."""
        if tls_start.settings is not None:
            return  # a user addon has already provided the settings.
        tls_start.settings = quic.QuicTlsSettings()

        # keep the following part in sync with `tls_start_client`
        assert isinstance(tls_start.conn, connection.Client)

        client: connection.Client = tls_start.conn
        server: connection.Server = tls_start.context.server

        entry = self.get_cert(tls_start.context)

        if not client.cipher_list and ctx.options.ciphers_client:
            client.cipher_list = ctx.options.ciphers_client.split(":")

        if ctx.options.add_upstream_certs_to_client_chain:  # pragma: no cover
            extra_chain_certs = server.certificate_list
        else:
            extra_chain_certs = []

        # set context parameters
        if client.cipher_list:
            tls_start.settings.cipher_suites = [
                CipherSuite[cipher] for cipher in client.cipher_list
            ]
        # if we don't have upstream ALPN, we allow all offered by the client
        tls_start.settings.alpn_protocols = [
            alpn.decode("ascii")
            for alpn in [alpn for alpn in (client.alpn, server.alpn) if alpn]
            or client.alpn_offers
        ]

        # set the certificates
        tls_start.settings.certificate = entry.cert._cert
        tls_start.settings.certificate_private_key = entry.privatekey
        tls_start.settings.certificate_chain = [
            cert._cert for cert in (*entry.chain_certs, *extra_chain_certs)
        ]

    def quic_start_server(self, tls_start: quic.QuicTlsData) -> None:
        """Establish QUIC between proxy and server."""
        if tls_start.settings is not None:
            return  # a user addon has already provided the settings.
        tls_start.settings = quic.QuicTlsSettings()

        # keep the following part in sync with `tls_start_server`
        assert isinstance(tls_start.conn, connection.Server)

        client: connection.Client = tls_start.context.client
        server: connection.Server = tls_start.conn
        assert server.address

        if ctx.options.ssl_insecure:
            tls_start.settings.verify_mode = ssl.CERT_NONE
        else:
            tls_start.settings.verify_mode = ssl.CERT_REQUIRED

        if server.sni is None:
            server.sni = client.sni or server.address[0]

        if not server.alpn_offers:
            if client.alpn_offers:
                server.alpn_offers = tuple(client.alpn_offers)
            else:
                # aioquic fails if no ALPN is offered, so use H3
                server.alpn_offers = tuple(alpn.encode("ascii") for alpn in H3_ALPN)

        if not server.cipher_list and ctx.options.ciphers_server:
            server.cipher_list = ctx.options.ciphers_server.split(":")

        # set context parameters
        if server.cipher_list:
            tls_start.settings.cipher_suites = [
                CipherSuite[cipher] for cipher in server.cipher_list
            ]
        if server.alpn_offers:
            tls_start.settings.alpn_protocols = [
                alpn.decode("ascii") for alpn in server.alpn_offers
            ]

        # set the certificates
        # NOTE client certificates are not supported
        tls_start.settings.ca_path = ctx.options.ssl_verify_upstream_trusted_confdir
        tls_start.settings.ca_file = ctx.options.ssl_verify_upstream_trusted_ca

    def running(self):
        # FIXME: We have a weird bug where the contract for configure is not followed and it is never called with
        # confdir or command_history as updated.
        self.configure("confdir")  # pragma: no cover

    def configure(self, updated):
        if (
            "certs" in updated
            or "confdir" in updated
            or "key_size" in updated
            or "cert_passphrase" in updated
        ):
            certstore_path = os.path.expanduser(ctx.options.confdir)
            self.certstore = certs.CertStore.from_store(
                path=certstore_path,
                basename=CONF_BASENAME,
                key_size=ctx.options.key_size,
                passphrase=ctx.options.cert_passphrase.encode("utf8")
                if ctx.options.cert_passphrase
                else None,
            )
            if self.certstore.default_ca.has_expired():
                logging.warning(
                    "The mitmproxy certificate authority has expired!\n"
                    "Please delete all CA-related files in your ~/.mitmproxy folder.\n"
                    "The CA will be regenerated automatically after restarting mitmproxy.\n"
                    "See https://docs.mitmproxy.org/stable/concepts-certificates/ for additional help.",
                )

            for certspec in ctx.options.certs:
                parts = certspec.split("=", 1)
                if len(parts) == 1:
                    parts = ["*", parts[0]]

                cert = Path(parts[1]).expanduser()
                if not cert.exists():
                    raise exceptions.OptionsError(
                        f"Certificate file does not exist: {cert}"
                    )
                try:
                    self.certstore.add_cert_file(
                        parts[0],
                        cert,
                        passphrase=ctx.options.cert_passphrase.encode("utf8")
                        if ctx.options.cert_passphrase
                        else None,
                    )
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Invalid certificate format for {cert}: {e}"
                    ) from e

        if "tls_ecdh_curve_client" in updated or "tls_ecdh_curve_server" in updated:
            for ecdh_curve in [
                ctx.options.tls_ecdh_curve_client,
                ctx.options.tls_ecdh_curve_server,
            ]:
                if ecdh_curve is not None:
                    try:
                        crypto.get_elliptic_curve(ecdh_curve)
                    except Exception as e:
                        raise exceptions.OptionsError(
                            f"Invalid ECDH curve: {ecdh_curve!r}"
                        ) from e

    def get_cert(self, conn_context: context.Context) -> certs.CertStoreEntry:
        """
        This function determines the Common Name (CN), Subject Alternative Names (SANs) and Organization Name
        our certificate should have and then fetches a matching cert from the certstore.
        """
        altnames: list[x509.GeneralName] = []
        organization: str | None = None

        # Use upstream certificate if available.
        if ctx.options.upstream_cert and conn_context.server.certificate_list:
            upstream_cert = conn_context.server.certificate_list[0]
            if upstream_cert.cn:
                altnames.append(_ip_or_dns_name(upstream_cert.cn))
            altnames.extend(upstream_cert.altnames)
            if upstream_cert.organization:
                organization = upstream_cert.organization

        # Add SNI or our local IP address.
        if conn_context.client.sni:
            altnames.append(_ip_or_dns_name(conn_context.client.sni))
        else:
            altnames.append(_ip_or_dns_name(conn_context.client.sockname[0]))

        # If we already know of a server address, include that in the SANs as well.
        if conn_context.server.address:
            altnames.append(_ip_or_dns_name(conn_context.server.address[0]))

        # only keep first occurrence of each hostname
        altnames = list(dict.fromkeys(altnames))

        # RFC 2818: If a subjectAltName extension of type dNSName is present, that MUST be used as the identity.
        # In other words, the Common Name is irrelevant then.
        cn = next((str(x.value) for x in altnames), None)
        return self.certstore.get_cert(cn, altnames, organization)


def _ip_or_dns_name(val: str) -> x509.GeneralName:
    """Convert a string into either an x509.IPAddress or x509.DNSName object."""
    try:
        ip = ipaddress.ip_address(val)
    except ValueError:
        return x509.DNSName(val.encode("idna").decode())
    else:
        return x509.IPAddress(ip)
