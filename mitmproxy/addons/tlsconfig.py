import os
from typing import List, Optional, Tuple, TypedDict, Any

from OpenSSL import SSL, crypto
from mitmproxy import certs, ctx, exceptions
from mitmproxy.net import tls as net_tls
from mitmproxy.options import CONF_BASENAME
from mitmproxy.proxy import context
from mitmproxy.proxy.layers import tls

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://ssl-config.mozilla.org/#config=old
DEFAULT_CIPHERS = (
    'ECDHE-ECDSA-AES128-GCM-SHA256', 'ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-ECDSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES256-GCM-SHA384', 'ECDHE-ECDSA-CHACHA20-POLY1305', 'ECDHE-RSA-CHACHA20-POLY1305',
    'DHE-RSA-AES128-GCM-SHA256', 'DHE-RSA-AES256-GCM-SHA384', 'DHE-RSA-CHACHA20-POLY1305', 'ECDHE-ECDSA-AES128-SHA256',
    'ECDHE-RSA-AES128-SHA256', 'ECDHE-ECDSA-AES128-SHA', 'ECDHE-RSA-AES128-SHA', 'ECDHE-ECDSA-AES256-SHA384',
    'ECDHE-RSA-AES256-SHA384', 'ECDHE-ECDSA-AES256-SHA', 'ECDHE-RSA-AES256-SHA', 'DHE-RSA-AES128-SHA256',
    'DHE-RSA-AES256-SHA256', 'AES128-GCM-SHA256', 'AES256-GCM-SHA384', 'AES128-SHA256', 'AES256-SHA256', 'AES128-SHA',
    'AES256-SHA', 'DES-CBC3-SHA'
)


class AppData(TypedDict):
    server_alpn: Optional[bytes]
    http2: bool


def alpn_select_callback(conn: SSL.Connection, options: List[bytes]) -> Any:
    app_data: AppData = conn.get_app_data()
    server_alpn = app_data["server_alpn"]
    http2 = app_data["http2"]
    if server_alpn and server_alpn in options:
        return server_alpn
    http_alpns = tls.HTTP_ALPNS if http2 else tls.HTTP1_ALPNS
    for alpn in options:  # client sends in order of preference, so we are nice and respect that.
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

    def tls_clienthello(self, tls_clienthello: tls.ClientHelloData):
        conn_context = tls_clienthello.context
        only_non_http_alpns = (
                conn_context.client.alpn_offers and
                all(x not in tls.HTTP_ALPNS for x in conn_context.client.alpn_offers)
        )
        tls_clienthello.establish_server_tls_first = conn_context.server.tls and (
                ctx.options.connection_strategy == "eager" or
                ctx.options.add_upstream_certs_to_client_chain or
                ctx.options.upstream_cert and (
                        only_non_http_alpns or
                        not conn_context.client.sni
                )
        )

    def tls_start(self, tls_start: tls.TlsStartData):
        if tls_start.conn == tls_start.context.client:
            self.create_client_proxy_ssl_conn(tls_start)
        else:
            self.create_proxy_server_ssl_conn(tls_start)

    def create_client_proxy_ssl_conn(self, tls_start: tls.TlsStartData) -> None:
        client: context.Client = tls_start.context.client
        server: context.Server = tls_start.context.server

        cert, key, chain_file = self.get_cert(tls_start.context)

        if not client.cipher_list and ctx.options.ciphers_client:
            client.cipher_list = ctx.options.ciphers_client.split(":")
        # don't assign to client.cipher_list, doesn't need to be stored.
        cipher_list = client.cipher_list or DEFAULT_CIPHERS

        ssl_ctx = net_tls.create_client_proxy_context(
            min_version=net_tls.Version[ctx.options.tls_version_client_min],
            max_version=net_tls.Version[ctx.options.tls_version_client_max],
            cipher_list=cipher_list,
            cert=cert,
            key=key,
            chain_file=chain_file,
            request_client_cert=False,
            alpn_select_callback=alpn_select_callback,
            extra_chain_certs=server.certificate_list,
            dhparams=self.certstore.dhparams,
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        tls_start.ssl_conn.set_app_data(AppData(
            server_alpn=server.alpn,
            http2=ctx.options.http2,
        ))
        tls_start.ssl_conn.set_accept_state()

    def create_proxy_server_ssl_conn(self, tls_start: tls.TlsStartData) -> None:
        client: context.Client = tls_start.context.client
        server: context.Server = tls_start.context.server
        assert server.address

        if ctx.options.ssl_insecure:
            verify = net_tls.Verify.VERIFY_NONE
        else:
            verify = net_tls.Verify.VERIFY_PEER

        if server.sni is True:
            server.sni = client.sni or server.address[0].encode()
        sni = server.sni or None  # make sure that false-y values are None

        if not server.alpn_offers:
            if client.alpn_offers:
                if ctx.options.http2:
                    server.alpn_offers = tuple(client.alpn_offers)
                else:
                    server.alpn_offers = tuple(x for x in client.alpn_offers if x != b"h2")
            elif client.tls_established:
                # We would perfectly support HTTP/1 -> HTTP/2, but we want to keep things on the same protocol version.
                # There are some edge cases where we want to mirror the regular server's behavior accurately,
                # for example header capitalization.
                server.alpn_offers = []
            elif ctx.options.http2:
                server.alpn_offers = tls.HTTP_ALPNS
            else:
                server.alpn_offers = tls.HTTP1_ALPNS

        if not server.cipher_list and ctx.options.ciphers_server:
            server.cipher_list = ctx.options.ciphers_server.split(":")
        # don't assign to client.cipher_list, doesn't need to be stored.
        cipher_list = server.cipher_list or DEFAULT_CIPHERS

        client_cert: Optional[str] = None
        if ctx.options.client_certs:
            client_certs = os.path.expanduser(ctx.options.client_certs)
            if os.path.isfile(client_certs):
                client_cert = client_certs
            else:
                server_name: str = (server.sni or server.address[0].encode("idna")).decode()
                p = os.path.join(client_certs, f"{server_name}.pem")
                if os.path.isfile(p):
                    client_cert = p

        ssl_ctx = net_tls.create_proxy_server_context(
            min_version=net_tls.Version[ctx.options.tls_version_client_min],
            max_version=net_tls.Version[ctx.options.tls_version_client_max],
            cipher_list=cipher_list,
            verify=verify,
            sni=sni,
            ca_path=ctx.options.ssl_verify_upstream_trusted_confdir,
            ca_pemfile=ctx.options.ssl_verify_upstream_trusted_ca,
            client_cert=client_cert,
            alpn_protos=server.alpn_offers,
        )

        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        tls_start.ssl_conn.set_tlsext_host_name(server.sni)
        tls_start.ssl_conn.set_connect_state()

    def configure(self, updated):
        if "confdir" not in updated and "certs" not in updated:
            return

        certstore_path = os.path.expanduser(ctx.options.confdir)
        self.certstore = certs.CertStore.from_store(
            path=certstore_path,
            basename=CONF_BASENAME,
            key_size=ctx.options.key_size,
            passphrase=ctx.options.cert_passphrase.encode("utf8") if ctx.options.cert_passphrase else None,
        )
        for certspec in ctx.options.certs:
            parts = certspec.split("=", 1)
            if len(parts) == 1:
                parts = ["*", parts[0]]

            cert = os.path.expanduser(parts[1])
            if not os.path.exists(cert):
                raise exceptions.OptionsError(f"Certificate file does not exist: {cert}")
            try:
                self.certstore.add_cert_file(
                    parts[0],
                    cert,
                    passphrase=ctx.options.cert_passphrase.encode("utf8") if ctx.options.cert_passphrase else None,
                )
            except crypto.Error as e:
                raise exceptions.OptionsError(f"Invalid certificate format: {cert}") from e

    def get_cert(self, conn_context: context.Context) -> Tuple[certs.Cert, SSL.PKey, str]:
        """
        This function determines the Common Name (CN), Subject Alternative Names (SANs) and Organization Name
        our certificate should have and then fetches a matching cert from the certstore.
        """
        altnames: List[bytes] = []
        organization: Optional[bytes] = None

        # Use upstream certificate if available.
        if conn_context.server.certificate_list:
            upstream_cert = conn_context.server.certificate_list[0]
            if upstream_cert.cn:
                altnames.append(upstream_cert.cn)
            altnames.extend(upstream_cert.altnames)
            if upstream_cert.organization:
                organization = upstream_cert.organization

        # Add SNI. If not available, try the server address as well.
        if conn_context.client.sni:
            altnames.append(conn_context.client.sni)
        elif conn_context.server.address:
            altnames.append(conn_context.server.address[0].encode("idna"))

        # As a last resort, add *something* so that we have a certificate to serve.
        if not altnames:
            altnames.append(b"mitmproxy")

        # only keep first occurrence of each hostname
        altnames = list(dict.fromkeys(altnames))

        # RFC 2818: If a subjectAltName extension of type dNSName is present, that MUST be used as the identity.
        # In other words, the Common Name is irrelevant then.
        return self.certstore.get_cert(altnames[0], altnames, organization)
