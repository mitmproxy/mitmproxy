from __future__ import (absolute_import, print_function, division)

import struct
from construct import ConstructError

from netlib import tcp
import netlib.http.http2

from ..contrib.tls._constructs import ClientHello
from ..exceptions import ProtocolException
from .layer import Layer


class TlsLayer(Layer):
    def __init__(self, ctx, client_tls, server_tls):
        self.client_sni = None
        self.client_alpn_protocols = None

        super(TlsLayer, self).__init__(ctx)
        self._client_tls = client_tls
        self._server_tls = server_tls

        self._sni_from_server_change = None

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
        Thus, we manually peek into the connection and parse the ClientHello message to obtain both SNI and ALPN values.

        Further notes:
            - OpenSSL 1.0.2 introduces a callback that would help here:
              https://www.openssl.org/docs/ssl/SSL_CTX_set_cert_cb.html
            - The original mitmproxy issue is https://github.com/mitmproxy/mitmproxy/issues/427
        """

        client_tls_requires_server_cert = (
            self._client_tls and self._server_tls and not self.config.no_upstream_cert
        )

        self._parse_client_hello()

        if client_tls_requires_server_cert:
            self._establish_tls_with_client_and_server()
        elif self._client_tls:
            self._establish_tls_with_client()

        layer = self.ctx.next_layer(self)
        layer()

    def _get_client_hello(self):
        """
        Peek into the socket and read all records that contain the initial client hello message.

        Returns:
            The raw handshake packet bytes, without TLS record header(s).
        """
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
        return client_hello

    def _parse_client_hello(self):
        """
        Peek into the connection, read the initial client hello and parse it to obtain ALPN values.
        """
        raw_client_hello = self._get_client_hello()[4:]  # exclude handshake header.
        try:
            client_hello = ClientHello.parse(raw_client_hello)
        except ConstructError as e:
            self.log("Cannot parse Client Hello: %s" % repr(e), "error")
            self.log("Raw Client Hello:\r\n:%s" % raw_client_hello.encode("hex"), "debug")
            return

        for extension in client_hello.extensions:
            if extension.type == 0x00:
                if len(extension.server_names) != 1 or extension.server_names[0].type != 0:
                    self.log("Unknown Server Name Indication: %s" % extension.server_names, "error")
                self.client_sni = extension.server_names[0].name
            elif extension.type == 0x10:
                self.client_alpn_protocols = list(extension.alpn_protocols)

        self.log("Parsed Client Hello: sni=%s, alpn=%s" % (self.client_sni, self.client_alpn_protocols), "debug")

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
    def sni_for_server_connection(self):
        if self._sni_from_server_change is False:
            return None
        else:
            return self._sni_from_server_change or self.client_sni

    @property
    def alpn_for_client_connection(self):
        return self.server_conn.get_alpn_proto_negotiated()

    def __alpn_select_callback(self, conn_, options):
        """
        Once the client signals the alternate protocols it supports,
        we reconnect upstream with the same list and pass the server's choice down to the client.
        """

        # This gets triggered if we haven't established an upstream connection yet.
        default_alpn = netlib.http.http1.HTTP1Protocol.ALPN_PROTO_HTTP1
        # alpn_preference = netlib.http.http2.HTTP2Protocol.ALPN_PROTO_H2

        if self.alpn_for_client_connection in options:
            choice = bytes(self.alpn_for_client_connection)
        elif default_alpn in options:
            choice = bytes(default_alpn)
        else:
            choice = options[0]
        self.log("ALPN for client: %s" % choice, "debug")
        return choice

    def _establish_tls_with_client_and_server(self):
        self.ctx.connect()

        # If establishing TLS with the server fails, we try to establish TLS with the client nonetheless
        # to send an error message over TLS.
        try:
            self._establish_tls_with_server()
        except Exception as e:
            try:
                self._establish_tls_with_client()
            except:
                pass
            raise e

        self._establish_tls_with_client()

    def _establish_tls_with_client(self):
        self.log("Establish TLS with client", "debug")
        cert, key, chain_file = self._find_cert()

        try:
            self.client_conn.convert_to_ssl(
                cert, key,
                method=self.config.openssl_method_client,
                options=self.config.openssl_options_client,
                cipher_list=self.config.ciphers_client,
                dhparams=self.config.certstore.dhparams,
                chain_file=chain_file,
                alpn_select_callback=self.__alpn_select_callback,
            )
        except tcp.NetLibError as e:
            raise ProtocolException("Cannot establish TLS with client: %s" % repr(e), e)

    def _establish_tls_with_server(self):
        self.log("Establish TLS with server", "debug")
        try:
            # We only support http/1.1 and h2.
            # If the server only supports spdy (next to http/1.1), it may select that
            # and mitmproxy would enter TCP passthrough mode, which we want to avoid.
            deprecated_http2_variant = lambda x: x.startswith("h2-") or x.startswith("spdy")
            if self.client_alpn_protocols:
                alpn = filter(lambda x: not deprecated_http2_variant(x), self.client_alpn_protocols)
            else:
                alpn = None

            self.server_conn.establish_ssl(
                self.config.clientcerts,
                self.sni_for_server_connection,
                method=self.config.openssl_method_server,
                options=self.config.openssl_options_server,
                verify_options=self.config.openssl_verification_mode_server,
                ca_path=self.config.openssl_trusted_cadir_server,
                ca_pemfile=self.config.openssl_trusted_ca_server,
                cipher_list=self.config.ciphers_server,
                alpn_protos=alpn,
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
            raise ProtocolException("Cannot establish TLS with server: %s" % repr(e), e)
        except tcp.NetLibError as e:
            raise ProtocolException("Cannot establish TLS with server: %s" % repr(e), e)

        self.log("ALPN selected by server: %s" % self.alpn_for_client_connection, "debug")

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
