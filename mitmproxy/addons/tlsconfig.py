import os
from typing import List, Optional, Tuple, TypedDict, cast

from OpenSSL import SSL, crypto
from mitmproxy import certs, ctx, exceptions
from mitmproxy.net import tls as net_tls
from mitmproxy.options import CONF_BASENAME
from mitmproxy.proxy.protocol.tls import DEFAULT_CLIENT_CIPHERS
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.layers import tls


class AppData(TypedDict):
    server_alpn: Optional[bytes]
    http2: bool


def alpn_select_callback(conn: SSL.Connection, options: List[bytes]):
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
    certstore: certs.CertStore = None

    # TODO: We should support configuring TLS 1.3 cipher suites (https://github.com/mitmproxy/mitmproxy/issues/4260)
    # TODO: We should re-use SSL.Context options here, if only for TLS session resumption.
    #       This may require patches to pyOpenSSL, as some functionality is only exposed on contexts.
    # TODO: This addon should manage the following options itself, which are current defined in mitmproxy/options.py:
    #  - upstream_cert
    #  - add_upstream_certs_to_client_chain
    #  - ssl_version_client
    #  - ssl_version_server
    #  - ciphers_client
    #  - ciphers_server
    #  - key_size
    #  - certs
    #  - cert_passphrase
    #  - ssl_verify_upstream_trusted_ca
    #  - ssl_verify_upstream_trusted_confdir

    def get_cert(self, conn_context: context.Context) -> Tuple[certs.Cert, SSL.PKey, str]:
        """
        This function determines the Common Name (CN), Subject Alternative Names (SANs) and Organization Name
        our certificate should have and then fetches a matching cert from the certstore.
        """
        altnames: List[bytes] = []
        organization: Optional[str] = None

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
        tls_method, tls_options = net_tls.VERSION_CHOICES[ctx.options.ssl_version_client]
        cert, key, chain_file = self.get_cert(tls_start.context)
        ssl_ctx = net_tls.create_server_context(
            cert=cert,
            key=key,
            method=tls_method,
            options=tls_options,
            cipher_list=ctx.options.ciphers_client or DEFAULT_CLIENT_CIPHERS,
            dhparams=self.certstore.dhparams,
            chain_file=chain_file,
            alpn_select_callback=alpn_select_callback,
            extra_chain_certs=tls_start.context.server.certificate_list,
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        tls_start.ssl_conn.set_app_data(AppData(
            server_alpn=tls_start.context.server.alpn,
            http2=ctx.options.http2,
        ))
        tls_start.ssl_conn.set_accept_state()

    def create_proxy_server_ssl_conn(self, tls_start: tls.TlsStartData) -> None:
        client = tls_start.context.client
        server = cast(context.Server, tls_start.conn)

        if server.sni is True:
            server.sni = client.sni or server.address[0].encode()

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

        # We pass through the list of ciphers send by the client, because some HTTP/2 servers
        # will select a non-HTTP/2 compatible cipher from our default list and then hang up
        # because it's incompatible with h2.
        if not server.cipher_list:
            if ctx.options.ciphers_server:
                server.cipher_list = ctx.options.ciphers_server.split(":")
            elif client.cipher_list:
                # We used to filter for known ciphers here, but that doesn't seem to make sense.
                # According to OpenSSL docs, the control string str should be universally
                # usable and not depend on details of the library configuration (ciphers compiled in).
                server.cipher_list = list(client.cipher_list)

        args = net_tls.client_arguments_from_options(ctx.options)

        client_certs = args.pop("client_certs")
        client_cert: Optional[str] = None
        if client_certs:
            client_certs = os.path.expanduser(client_certs)
            if os.path.isfile(client_certs):
                client_cert = client_certs
            else:
                server_name: str = (server.sni or server.address[0].encode("idna")).decode()
                path = os.path.join(client_certs, f"{server_name}.pem")
                if os.path.exists(path):
                    client_cert = path

        args["cipher_list"] = ':'.join(server.cipher_list) if server.cipher_list else None
        ssl_ctx = net_tls.create_client_context(
            cert=client_cert,
            sni=server.sni.decode("idna"),  # TODO: Should pass-through here.
            alpn_protos=server.alpn_offers,
            **args
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        tls_start.ssl_conn.set_tlsext_host_name(server.sni)
        tls_start.ssl_conn.set_connect_state()

    def configure(self, updated):
        if self.certstore and not any(x in updated for x in ["confdir", "certs"]):
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
