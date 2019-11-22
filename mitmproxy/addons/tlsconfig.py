import os
from typing import Optional, Tuple

from OpenSSL import SSL, crypto

from mitmproxy import certs, ctx, exceptions
from mitmproxy.net import tls as net_tls
from mitmproxy.options import CONF_BASENAME
from mitmproxy.proxy.protocol.tls import CIPHER_ID_NAME_MAP, DEFAULT_CLIENT_CIPHERS
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.layers import tls


def alpn_select_callback(conn: SSL.Connection, options):
    server_alpn = conn.get_app_data()["server_alpn"]
    if server_alpn and server_alpn in options:
        return server_alpn
    for alpn in tls.HTTP_ALPNS:
        if alpn in options:
            return alpn
    else:
        # FIXME: pyOpenSSL requires that an ALPN is negotiated, we can't return SSL_TLSEXT_ERR_NOACK.
        return options[0]


class TlsConfig:
    certstore: certs.CertStore

    # TODO: We should re-use SSL.Context options here, if only for TLS session resumption.
    # This may require patches to pyOpenSSL, as some functionality is only exposed on contexts.

    def get_cert(self, context: context.Context) -> Tuple[certs.Cert, SSL.PKey, str]:
        # FIXME
        return self.certstore.get_cert(
            context.client.sni, [context.client.sni]
        )

    def tls_clienthello(self, tls_clienthello: tls.ClientHelloHookData):
        context = tls_clienthello.context
        only_non_http_alpns = (
                context.client.alpn_offers and
                all(x not in tls.HTTP_ALPNS for x in context.client.alpn_offers)
        )
        tls_clienthello.establish_server_tls_first = context.server.tls and (
                context.options.connection_strategy == "eager" or
                context.options.add_upstream_certs_to_client_chain or
                context.options.upstream_cert and (
                        only_non_http_alpns or
                        not context.client.sni
                )
        )

    def tls_start(self, tls_start: tls.StartHookData):
        if tls_start.conn == tls_start.context.client:
            self.create_client_proxy_ssl_conn(tls_start)
        else:
            self.create_proxy_server_ssl_conn(tls_start)

    def create_client_proxy_ssl_conn(self, tls_start: tls.StartHookData) -> None:
        tls_method, tls_options = net_tls.VERSION_CHOICES[ctx.options.ssl_version_client]
        cert, key, chain_file = self.get_cert(tls_start.context)
        if ctx.options.add_upstream_certs_to_client_chain:
            raise NotImplementedError()
        else:
            extra_chain_certs = None
        ssl_ctx = net_tls.create_server_context(
            cert=cert,
            key=key,
            method=tls_method,
            options=tls_options,
            cipher_list=ctx.options.ciphers_client or DEFAULT_CLIENT_CIPHERS,
            dhparams=self.certstore.dhparams,
            chain_file=chain_file,
            alpn_select_callback=alpn_select_callback,
            extra_chain_certs=extra_chain_certs,
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)
        tls_start.ssl_conn.set_app_data({
            "server_alpn": tls_start.context.server.alpn
        })

    def create_proxy_server_ssl_conn(self, tls_start: tls.StartHookData) -> None:
        client = tls_start.context.client
        server: context.Server = tls_start.conn

        if server.sni is True:
            server.sni = client.sni or server.address[0].encode()

        if not server.alpn_offers:
            if client.alpn:
                server.alpn_offers = [client.alpn]
            elif client.alpn_offers:
                server.alpn_offers = client.alpn_offers

        # We pass through the list of ciphers send by the client, because some HTTP/2 servers
        # will select a non-HTTP/2 compatible cipher from our default list and then hang up
        # because it's incompatible with h2.
        if not server.cipher_list:
            if ctx.options.ciphers_server:
                server.cipher_list = ctx.options.ciphers_server.split(":")
            elif client.cipher_list:
                server.cipher_list = [
                    x for x in client.cipher_list
                    if x in CIPHER_ID_NAME_MAP
                ]

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
            sni=server.sni.decode("idna"),  # FIXME: Should pass-through here.
            alpn_protos=server.alpn_offers,
            **args
        )
        tls_start.ssl_conn = SSL.Connection(ssl_ctx)

    def configure(self, updated):
        if not any(x in updated for x in ["confdir", "certs"]):
            return

        certstore_path = os.path.expanduser(ctx.options.confdir)
        if not os.path.exists(os.path.dirname(certstore_path)):
            raise exceptions.OptionsError(
                f"Certificate Authority parent directory does not exist: {os.path.dirname(certstore_path)}")
        self.certstore = certs.CertStore.from_store(
            path=certstore_path,
            basename=CONF_BASENAME,
            key_size=ctx.options.key_size
        )
        for certspec in ctx.options.certs:
            parts = certspec.split("=", 1)
            if len(parts) == 1:
                parts = ["*", parts[0]]

            cert = os.path.expanduser(parts[1])
            if not os.path.exists(cert):
                raise exceptions.OptionsError(f"Certificate file does not exist: {cert}")
            try:
                self.certstore.add_cert_file(parts[0], cert)
            except crypto.Error as e:
                raise exceptions.OptionsError(f"Invalid certificate format: {cert}") from e
