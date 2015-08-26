from __future__ import (absolute_import, print_function, division)

from ..contrib.tls._constructs import ClientHello

from netlib import tcp
import netlib.http.http2

from ..exceptions import ProtocolException
from .layer import Layer


class TlsLayer(Layer):
    def __init__(self, ctx, client_tls, server_tls):
        self.client_sni = None
        self.client_alpn_protos = None

        super(TlsLayer, self).__init__(ctx)
        self._client_tls = client_tls
        self._server_tls = server_tls

        self._sni_from_server_change = None
        self.__server_tls_exception = None

    def __call__(self):
        """
        The strategy for establishing SSL is as follows:
            First, we determine whether we need the server cert to establish ssl with the client.
            If so, we first connect to the server and then to the client.
            If not, we only connect to the client and do the server_ssl lazily on a Connect message.

        An additional complexity is that establish ssl with the server may require a SNI value from the client.
        In an ideal world, we'd do the following:
            1. Start the SSL handshake with the client
            2. Check if the client sends a SNI.
            3. Pause the client handshake, establish SSL with the server.
            4. Finish the client handshake with the certificate from the server.
        There's just one issue: We cannot get a callback from OpenSSL if the client doesn't send a SNI. :(
        Thus, we resort to the following workaround when establishing SSL with the server:
            1. Try to establish SSL with the server without SNI. If this fails, we ignore it.
            2. Establish SSL with client.
                - If there's a SNI callback, reconnect to the server with SNI.
                - If not and the server connect failed, raise the original exception.
        Further notes:
            - OpenSSL 1.0.2 introduces a callback that would help here:
              https://www.openssl.org/docs/ssl/SSL_CTX_set_cert_cb.html
            - The original mitmproxy issue is https://github.com/mitmproxy/mitmproxy/issues/427
        """
        import struct

        # Read all records that contain the initial Client Hello message.
        client_hello = ""
        client_hello_size = 1
        offset = 0
        while len(client_hello) < client_hello_size:
            record_header = self.client_conn.rfile.peek(offset+5)[offset:]
            record_size = struct.unpack("!H", record_header[3:])[0] + 5
            record_body = self.client_conn.rfile.peek(offset+record_size)[offset+5:]
            client_hello += record_body
            offset += record_size
            client_hello_size = struct.unpack("!I", '\x00' + client_hello[1:4])[0] + 4

        client_hello = ClientHello.parse(client_hello[4:])

        for extension in client_hello.extensions:
            if extension.type == 0x00:
                host = extension.server_names[0].name
            if extension.type == 0x10:
                alpn = extension.alpn_protocols

        client_tls_requires_server_cert = (
            self._client_tls and self._server_tls and not self.config.no_upstream_cert
        )

        if client_tls_requires_server_cert:
            self._establish_tls_with_client_and_server()
        elif self._client_tls:
            self._establish_tls_with_client()

        layer = self.ctx.next_layer(self)
        layer()

    def connect(self):
        if not self.server_conn:
            self.ctx.connect()
        if self._server_tls and not self.server_conn.tls_established:
            self._establish_tls_with_server()

    def reconnect(self):
        self.ctx.reconnect()
        if self._server_tls and not self.server_conn.tls_established:
            self._establish_tls_with_server()

    def set_server(self, address, server_tls, sni, depth=1):
        self.ctx.set_server(address, server_tls, sni, depth)
        if server_tls is not None:
            self._sni_from_server_change = sni
            self._server_tls = server_tls

    @property
    def sni_for_upstream_connection(self):
        if self._sni_from_server_change is False:
            return None
        else:
            return self._sni_from_server_change or self.client_sni

    def _establish_tls_with_client_and_server(self):
        """
        This function deals with the problem that the server may require a SNI value from the client.
        """

        # First, try to connect to the server.
        self.ctx.connect()
        server_err = None
        try:
            self._establish_tls_with_server()
        except ProtocolException as e:
            server_err = e

        self._establish_tls_with_client()

        if server_err and not self.client_sni:
            raise server_err

    def __handle_sni(self, connection):
        """
        This callback gets called during the TLS handshake with the client.
        The client has just sent the Sever Name Indication (SNI).
        """
        old_upstream_sni = self.sni_for_upstream_connection

        sn = connection.get_servername()
        if not sn:
            return

        self.client_sni = sn.decode("utf8").encode("idna")

        server_sni_changed = (old_upstream_sni != self.sni_for_upstream_connection)
        server_conn_with_tls_exists = (self.server_conn and self._server_tls)
        if server_sni_changed and server_conn_with_tls_exists:
            try:
                self.reconnect()
            except Exception as e:
                self.__server_tls_exception = e

        # Now, change client context to reflect possibly changed certificate:
        cert, key, chain_file = self._find_cert()
        new_context = self.client_conn.create_ssl_context(
            cert, key,
            method=self.config.openssl_method_client,
            options=self.config.openssl_options_client,
            cipher_list=self.config.ciphers_client,
            dhparams=self.config.certstore.dhparams,
            chain_file=chain_file,
            alpn_select_callback=self.__handle_alpn_select,
        )
        connection.set_context(new_context)

    def __handle_alpn_select(self, conn_, options):
        """
        Once the client signals the alternate protocols it supports,
        we reconnect upstream with the same list and pass the server's choice down to the client.
        """
        # TODO: change to something meaningful?
        # alpn_preference = netlib.http.http1.HTTP1Protocol.ALPN_PROTO_HTTP1
        alpn_preference = netlib.http.http2.HTTP2Protocol.ALPN_PROTO_H2

        # TODO: Don't reconnect twice?
        upstream_alpn_changed = (self.client_alpn_protos != options)
        server_conn_with_tls_exists = (self.server_conn and self._server_tls)
        if upstream_alpn_changed and server_conn_with_tls_exists:
            try:
                self.reconnect()
            except Exception as e:
                self.__server_tls_exception = e

        self.client_alpn_protos = options

        if alpn_preference in options:
            return bytes(alpn_preference)
        else:  # pragma no cover
            return options[0]

    def _establish_tls_with_client(self):
        self.log("Establish TLS with client", "debug")
        cert, key, chain_file = self._find_cert()

        try:
            self.client_conn.convert_to_ssl(
                cert, key,
                method=self.config.openssl_method_client,
                options=self.config.openssl_options_client,
                handle_sni=self.__handle_sni,
                cipher_list=self.config.ciphers_client,
                dhparams=self.config.certstore.dhparams,
                chain_file=chain_file,
                alpn_select_callback=self.__handle_alpn_select,
            )
        except tcp.NetLibError as e:
            print("alpn: %s" % self.client_alpn_protos)
            raise ProtocolException(repr(e), e)

        # Do not raise server tls exceptions immediately.
        # We want to try to finish the client handshake so that other layers can send error messages over it.
        if self.__server_tls_exception:
            raise self.__server_tls_exception

    def _establish_tls_with_server(self):
        self.log("Establish TLS with server", "debug")
        try:
            self.server_conn.establish_ssl(
                self.config.clientcerts,
                self.sni_for_upstream_connection,
                method=self.config.openssl_method_server,
                options=self.config.openssl_options_server,
                verify_options=self.config.openssl_verification_mode_server,
                ca_path=self.config.openssl_trusted_cadir_server,
                ca_pemfile=self.config.openssl_trusted_ca_server,
                cipher_list=self.config.ciphers_server,
                alpn_protos=self.client_alpn_protos,
            )
            tls_cert_err = self.server_conn.ssl_verification_error
            if tls_cert_err is not None:
                self.log(
                    "TLS verification failed for upstream server at depth %s with error: %s" %
                    (tls_cert_err['depth'], tls_cert_err['errno']),
                    "error")
                self.log("Ignoring server verification error, continuing with connection", "error")
        except tcp.NetLibInvalidCertificateError as e:
            tls_cert_err = self.server_conn.ssl_verification_error
            self.log(
                "TLS verification failed for upstream server at depth %s with error: %s" %
                (tls_cert_err['depth'], tls_cert_err['errno']),
                "error")
            self.log("Aborting connection attempt", "error")
            raise ProtocolException(repr(e), e)
        except tcp.NetLibError as e:
            raise ProtocolException(repr(e), e)

    def _find_cert(self):
        host = self.server_conn.address.host
        sans = set()
        # Incorporate upstream certificate
        if self.server_conn and self.server_conn.tls_established and (not self.config.no_upstream_cert):
            upstream_cert = self.server_conn.cert
            sans.update(upstream_cert.altnames)
            if upstream_cert.cn:
                sans.add(host)
                host = upstream_cert.cn.decode("utf8").encode("idna")
        # Also add SNI values.
        if self.client_sni:
            sans.add(self.client_sni)
        if self._sni_from_server_change:
            sans.add(self._sni_from_server_change)

        sans.discard(host)
        return self.config.certstore.get_cert(host, list(sans))
