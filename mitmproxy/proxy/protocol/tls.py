from typing import Optional  # noqa
from typing import Union

from mitmproxy import exceptions
from mitmproxy.net import tls as net_tls
from mitmproxy.proxy.protocol import base

# taken from https://testssl.sh/openssl-rfc.mapping.html
CIPHER_ID_NAME_MAP = {
    0x00: 'NULL-MD5',
    0x01: 'NULL-MD5',
    0x02: 'NULL-SHA',
    0x03: 'EXP-RC4-MD5',
    0x04: 'RC4-MD5',
    0x05: 'RC4-SHA',
    0x06: 'EXP-RC2-CBC-MD5',
    0x07: 'IDEA-CBC-SHA',
    0x08: 'EXP-DES-CBC-SHA',
    0x09: 'DES-CBC-SHA',
    0x0a: 'DES-CBC3-SHA',
    0x0b: 'EXP-DH-DSS-DES-CBC-SHA',
    0x0c: 'DH-DSS-DES-CBC-SHA',
    0x0d: 'DH-DSS-DES-CBC3-SHA',
    0x0e: 'EXP-DH-RSA-DES-CBC-SHA',
    0x0f: 'DH-RSA-DES-CBC-SHA',
    0x10: 'DH-RSA-DES-CBC3-SHA',
    0x11: 'EXP-EDH-DSS-DES-CBC-SHA',
    0x12: 'EDH-DSS-DES-CBC-SHA',
    0x13: 'EDH-DSS-DES-CBC3-SHA',
    0x14: 'EXP-EDH-RSA-DES-CBC-SHA',
    0x15: 'EDH-RSA-DES-CBC-SHA',
    0x16: 'EDH-RSA-DES-CBC3-SHA',
    0x17: 'EXP-ADH-RC4-MD5',
    0x18: 'ADH-RC4-MD5',
    0x19: 'EXP-ADH-DES-CBC-SHA',
    0x1a: 'ADH-DES-CBC-SHA',
    0x1b: 'ADH-DES-CBC3-SHA',
    # 0x1c: ,
    # 0x1d: ,
    0x1e: 'KRB5-DES-CBC-SHA',
    0x1f: 'KRB5-DES-CBC3-SHA',
    0x20: 'KRB5-RC4-SHA',
    0x21: 'KRB5-IDEA-CBC-SHA',
    0x22: 'KRB5-DES-CBC-MD5',
    0x23: 'KRB5-DES-CBC3-MD5',
    0x24: 'KRB5-RC4-MD5',
    0x25: 'KRB5-IDEA-CBC-MD5',
    0x26: 'EXP-KRB5-DES-CBC-SHA',
    0x27: 'EXP-KRB5-RC2-CBC-SHA',
    0x28: 'EXP-KRB5-RC4-SHA',
    0x29: 'EXP-KRB5-DES-CBC-MD5',
    0x2a: 'EXP-KRB5-RC2-CBC-MD5',
    0x2b: 'EXP-KRB5-RC4-MD5',
    0x2f: 'AES128-SHA',
    0x30: 'DH-DSS-AES128-SHA',
    0x31: 'DH-RSA-AES128-SHA',
    0x32: 'DHE-DSS-AES128-SHA',
    0x33: 'DHE-RSA-AES128-SHA',
    0x34: 'ADH-AES128-SHA',
    0x35: 'AES256-SHA',
    0x36: 'DH-DSS-AES256-SHA',
    0x37: 'DH-RSA-AES256-SHA',
    0x38: 'DHE-DSS-AES256-SHA',
    0x39: 'DHE-RSA-AES256-SHA',
    0x3a: 'ADH-AES256-SHA',
    0x3b: 'NULL-SHA256',
    0x3c: 'AES128-SHA256',
    0x3d: 'AES256-SHA256',
    0x3e: 'DH-DSS-AES128-SHA256',
    0x3f: 'DH-RSA-AES128-SHA256',
    0x40: 'DHE-DSS-AES128-SHA256',
    0x41: 'CAMELLIA128-SHA',
    0x42: 'DH-DSS-CAMELLIA128-SHA',
    0x43: 'DH-RSA-CAMELLIA128-SHA',
    0x44: 'DHE-DSS-CAMELLIA128-SHA',
    0x45: 'DHE-RSA-CAMELLIA128-SHA',
    0x46: 'ADH-CAMELLIA128-SHA',
    0x62: 'EXP1024-DES-CBC-SHA',
    0x63: 'EXP1024-DHE-DSS-DES-CBC-SHA',
    0x64: 'EXP1024-RC4-SHA',
    0x65: 'EXP1024-DHE-DSS-RC4-SHA',
    0x66: 'DHE-DSS-RC4-SHA',
    0x67: 'DHE-RSA-AES128-SHA256',
    0x68: 'DH-DSS-AES256-SHA256',
    0x69: 'DH-RSA-AES256-SHA256',
    0x6a: 'DHE-DSS-AES256-SHA256',
    0x6b: 'DHE-RSA-AES256-SHA256',
    0x6c: 'ADH-AES128-SHA256',
    0x6d: 'ADH-AES256-SHA256',
    0x80: 'GOST94-GOST89-GOST89',
    0x81: 'GOST2001-GOST89-GOST89',
    0x82: 'GOST94-NULL-GOST94',
    0x83: 'GOST2001-GOST89-GOST89',
    0x84: 'CAMELLIA256-SHA',
    0x85: 'DH-DSS-CAMELLIA256-SHA',
    0x86: 'DH-RSA-CAMELLIA256-SHA',
    0x87: 'DHE-DSS-CAMELLIA256-SHA',
    0x88: 'DHE-RSA-CAMELLIA256-SHA',
    0x89: 'ADH-CAMELLIA256-SHA',
    0x8a: 'PSK-RC4-SHA',
    0x8b: 'PSK-3DES-EDE-CBC-SHA',
    0x8c: 'PSK-AES128-CBC-SHA',
    0x8d: 'PSK-AES256-CBC-SHA',
    # 0x8e: ,
    # 0x8f: ,
    # 0x90: ,
    # 0x91: ,
    # 0x92: ,
    # 0x93: ,
    # 0x94: ,
    # 0x95: ,
    0x96: 'SEED-SHA',
    0x97: 'DH-DSS-SEED-SHA',
    0x98: 'DH-RSA-SEED-SHA',
    0x99: 'DHE-DSS-SEED-SHA',
    0x9a: 'DHE-RSA-SEED-SHA',
    0x9b: 'ADH-SEED-SHA',
    0x9c: 'AES128-GCM-SHA256',
    0x9d: 'AES256-GCM-SHA384',
    0x9e: 'DHE-RSA-AES128-GCM-SHA256',
    0x9f: 'DHE-RSA-AES256-GCM-SHA384',
    0xa0: 'DH-RSA-AES128-GCM-SHA256',
    0xa1: 'DH-RSA-AES256-GCM-SHA384',
    0xa2: 'DHE-DSS-AES128-GCM-SHA256',
    0xa3: 'DHE-DSS-AES256-GCM-SHA384',
    0xa4: 'DH-DSS-AES128-GCM-SHA256',
    0xa5: 'DH-DSS-AES256-GCM-SHA384',
    0xa6: 'ADH-AES128-GCM-SHA256',
    0xa7: 'ADH-AES256-GCM-SHA384',
    0x5600: 'TLS_FALLBACK_SCSV',
    0xc001: 'ECDH-ECDSA-NULL-SHA',
    0xc002: 'ECDH-ECDSA-RC4-SHA',
    0xc003: 'ECDH-ECDSA-DES-CBC3-SHA',
    0xc004: 'ECDH-ECDSA-AES128-SHA',
    0xc005: 'ECDH-ECDSA-AES256-SHA',
    0xc006: 'ECDHE-ECDSA-NULL-SHA',
    0xc007: 'ECDHE-ECDSA-RC4-SHA',
    0xc008: 'ECDHE-ECDSA-DES-CBC3-SHA',
    0xc009: 'ECDHE-ECDSA-AES128-SHA',
    0xc00a: 'ECDHE-ECDSA-AES256-SHA',
    0xc00b: 'ECDH-RSA-NULL-SHA',
    0xc00c: 'ECDH-RSA-RC4-SHA',
    0xc00d: 'ECDH-RSA-DES-CBC3-SHA',
    0xc00e: 'ECDH-RSA-AES128-SHA',
    0xc00f: 'ECDH-RSA-AES256-SHA',
    0xc010: 'ECDHE-RSA-NULL-SHA',
    0xc011: 'ECDHE-RSA-RC4-SHA',
    0xc012: 'ECDHE-RSA-DES-CBC3-SHA',
    0xc013: 'ECDHE-RSA-AES128-SHA',
    0xc014: 'ECDHE-RSA-AES256-SHA',
    0xc015: 'AECDH-NULL-SHA',
    0xc016: 'AECDH-RC4-SHA',
    0xc017: 'AECDH-DES-CBC3-SHA',
    0xc018: 'AECDH-AES128-SHA',
    0xc019: 'AECDH-AES256-SHA',
    0xc01a: 'SRP-3DES-EDE-CBC-SHA',
    0xc01b: 'SRP-RSA-3DES-EDE-CBC-SHA',
    0xc01c: 'SRP-DSS-3DES-EDE-CBC-SHA',
    0xc01d: 'SRP-AES-128-CBC-SHA',
    0xc01e: 'SRP-RSA-AES-128-CBC-SHA',
    0xc01f: 'SRP-DSS-AES-128-CBC-SHA',
    0xc020: 'SRP-AES-256-CBC-SHA',
    0xc021: 'SRP-RSA-AES-256-CBC-SHA',
    0xc022: 'SRP-DSS-AES-256-CBC-SHA',
    0xc023: 'ECDHE-ECDSA-AES128-SHA256',
    0xc024: 'ECDHE-ECDSA-AES256-SHA384',
    0xc025: 'ECDH-ECDSA-AES128-SHA256',
    0xc026: 'ECDH-ECDSA-AES256-SHA384',
    0xc027: 'ECDHE-RSA-AES128-SHA256',
    0xc028: 'ECDHE-RSA-AES256-SHA384',
    0xc029: 'ECDH-RSA-AES128-SHA256',
    0xc02a: 'ECDH-RSA-AES256-SHA384',
    0xc02b: 'ECDHE-ECDSA-AES128-GCM-SHA256',
    0xc02c: 'ECDHE-ECDSA-AES256-GCM-SHA384',
    0xc02d: 'ECDH-ECDSA-AES128-GCM-SHA256',
    0xc02e: 'ECDH-ECDSA-AES256-GCM-SHA384',
    0xc02f: 'ECDHE-RSA-AES128-GCM-SHA256',
    0xc030: 'ECDHE-RSA-AES256-GCM-SHA384',
    0xc031: 'ECDH-RSA-AES128-GCM-SHA256',
    0xc032: 'ECDH-RSA-AES256-GCM-SHA384',
    0xcc13: 'ECDHE-RSA-CHACHA20-POLY1305',
    0xcc14: 'ECDHE-ECDSA-CHACHA20-POLY1305',
    0xcc15: 'DHE-RSA-CHACHA20-POLY1305',
    0xff00: 'GOST-MD5',
    0xff01: 'GOST-GOST94',
    0xff02: 'GOST-GOST89MAC',
    0xff03: 'GOST-GOST89STREAM',
    0x010080: 'RC4-MD5',
    0x020080: 'EXP-RC4-MD5',
    0x030080: 'RC2-CBC-MD5',
    0x040080: 'EXP-RC2-CBC-MD5',
    0x050080: 'IDEA-CBC-MD5',
    0x060040: 'DES-CBC-MD5',
    0x0700c0: 'DES-CBC3-MD5',
    0x080080: 'RC4-64-MD5',
}

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://ssl-config.mozilla.org/#config=old
DEFAULT_CLIENT_CIPHERS = (
    "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:"
    "DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:"
    "ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:"
    "ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256:AES128-GCM-SHA256:"
    "AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA"
)


class TlsLayer(base.Layer):
    """
    The TLS layer implements transparent TLS connections.

    It exposes the following API to child layers:

        - :py:meth:`set_server_tls` to modify TLS settings for the server connection.
        - :py:attr:`server_tls`, :py:attr:`server_sni` as read-only attributes describing the current TLS settings for
          the server connection.
    """

    def __init__(self, ctx, client_tls, server_tls, custom_server_sni=None):
        super().__init__(ctx)
        self._client_tls = client_tls
        self._server_tls = server_tls

        self._custom_server_sni = custom_server_sni
        self._client_hello: Optional[net_tls.ClientHello] = None

    def __call__(self):
        """
        The strategy for establishing TLS is as follows:
            First, we determine whether we need the server cert to establish ssl with the client.
            If so, we first connect to the server and then to the client.
            If not, we only connect to the client and do the server handshake lazily.

        An additional complexity is that we need to mirror SNI and ALPN from the client when connecting to the server.
        We manually peek into the connection and parse the ClientHello message to obtain these values.
        """
        if self._client_tls:
            # Peek into the connection, read the initial client hello and parse it to obtain SNI and ALPN values.
            try:
                self._client_hello = net_tls.ClientHello.from_file(self.client_conn.rfile)
            except exceptions.TlsProtocolException as e:
                self.log("Cannot parse Client Hello: %s" % repr(e), "error")
                # Without knowning the ClientHello we cannot proceed in this connection.
                return

        # Do we need to do a server handshake now?
        # There are two reasons why we would want to establish TLS with the server now:
        #  1. If we already have an existing server connection and server_tls is True,
        #     we need to establish TLS now because .connect() will not be called anymore.
        #  2. We may need information from the server connection for the client handshake.
        #
        # A couple of factors influence (2):
        #  2.1 There actually is (or will be) a TLS-enabled upstream connection
        #  2.2 An upstream connection is not wanted by the user if --no-upstream-cert is passed.
        #  2.3 An upstream connection is implied by add_upstream_certs_to_client_chain
        #  2.4 The client wants to negotiate an alternative protocol in its handshake, we need to find out
        #      what is supported by the server
        #  2.5 The client did not sent a SNI value, we don't know the certificate subject.
        client_tls_requires_server_connection = (
            self._server_tls and
            self.config.options.upstream_cert and
            (
                self.config.options.add_upstream_certs_to_client_chain or
                self._client_tls and (
                    self._client_hello.alpn_protocols or
                    not self._client_hello.sni
                )
            )
        )
        establish_server_tls_now = (
            (self.server_conn.connected() and self._server_tls) or
            client_tls_requires_server_connection
        )

        if self._client_tls and establish_server_tls_now:
            self._establish_tls_with_client_and_server()
        elif self._client_tls:
            self._establish_tls_with_client()
        elif establish_server_tls_now:
            self._establish_tls_with_server()

        layer = self.ctx.next_layer(self)
        layer()

    def __repr__(self):  # pragma: no cover
        if self._client_tls and self._server_tls:
            return "TlsLayer(client and server)"
        elif self._client_tls:
            return "TlsLayer(client)"
        elif self._server_tls:
            return "TlsLayer(server)"
        else:
            return "TlsLayer(inactive)"

    def connect(self):
        if not self.server_conn.connected():
            self.ctx.connect()
        if self._server_tls and not self.server_conn.tls_established:
            self._establish_tls_with_server()

    def set_server_tls(self, server_tls: bool, sni: Union[str, None, bool] = None) -> None:
        """
        Set the TLS settings for the next server connection that will be established.
        This function will not alter an existing connection.

        Args:
            server_tls: Shall we establish TLS with the server?
            sni: ``str`` for a custom SNI value,
                ``None`` for the client SNI value,
                ``False`` if no SNI value should be sent.
        """
        self._server_tls = server_tls
        self._custom_server_sni = sni

    @property
    def server_tls(self):
        """
        ``True``, if the next server connection that will be established should be upgraded to TLS.
        """
        return self._server_tls

    @property
    def server_sni(self) -> Optional[str]:
        """
        The Server Name Indication we want to send with the next server TLS handshake.
        """
        if self._custom_server_sni is False:
            return None
        elif self._custom_server_sni:
            return self._custom_server_sni
        elif self._client_hello and self._client_hello.sni:
            return self._client_hello.sni.decode("idna")
        else:
            return None

    @property
    def alpn_for_client_connection(self):
        return self.server_conn.get_alpn_proto_negotiated()

    def __alpn_select_callback(self, conn_, options):
        # This gets triggered if we haven't established an upstream connection yet.
        default_alpn = b'http/1.1'

        if self.alpn_for_client_connection in options:
            choice = bytes(self.alpn_for_client_connection)
        elif default_alpn in options:
            choice = bytes(default_alpn)
        else:
            choice = options[0]
        self.log("ALPN for client: %s" % choice, "debug")
        return choice

    def _establish_tls_with_client_and_server(self):
        try:
            self.ctx.connect()
            self._establish_tls_with_server()
        except Exception:
            # If establishing TLS with the server fails, we try to establish TLS with the client nonetheless
            # to send an error message over TLS.
            try:
                self._establish_tls_with_client()
            except:
                pass
            raise

        self._establish_tls_with_client()

    def _establish_tls_with_client(self):
        self.log("Establish TLS with client", "debug")
        cert, key, chain_file = self._find_cert()

        if self.config.options.add_upstream_certs_to_client_chain:
            extra_certs = self.server_conn.server_certs
        else:
            extra_certs = None

        try:
            tls_method, tls_options = net_tls.VERSION_CHOICES[self.config.options.ssl_version_client]
            self.client_conn.convert_to_tls(
                cert, key,
                method=tls_method,
                options=tls_options,
                cipher_list=self.config.options.ciphers_client or DEFAULT_CLIENT_CIPHERS,
                dhparams=self.config.certstore.dhparams,
                chain_file=chain_file,
                alpn_select_callback=self.__alpn_select_callback,
                extra_chain_certs=extra_certs,
            )
            # Some TLS clients will not fail the handshake,
            # but will immediately throw an "unexpected eof" error on the first read.
            # The reason for this might be difficult to find, so we try to peek here to see if it
            # raises ann error.
            self.client_conn.rfile.peek(1)
        except exceptions.TlsException as e:
            sni_str = self._client_hello.sni and self._client_hello.sni.decode("idna")
            raise exceptions.ClientHandshakeException(
                "Cannot establish TLS with client (sni: {sni}): {e}".format(
                    sni=sni_str, e=repr(e)
                ),
                sni_str or repr(self.server_conn.address)
            )

    def _establish_tls_with_server(self):
        self.log("Establish TLS with server", "debug")
        try:
            alpn = None
            if self._client_tls:
                if self._client_hello.alpn_protocols:
                    # We only support http/1.1 and h2.
                    # If the server only supports spdy (next to http/1.1), it may select that
                    # and mitmproxy would enter TCP passthrough mode, which we want to avoid.
                    alpn = [
                        x for x in self._client_hello.alpn_protocols if
                        not (x.startswith(b"h2-") or x.startswith(b"spdy"))
                    ]
                if alpn and b"h2" in alpn and not self.config.options.http2:
                    alpn.remove(b"h2")

            if self.client_conn.tls_established and self.client_conn.get_alpn_proto_negotiated():
                # If the client has already negotiated an ALP, then force the
                # server to use the same. This can only happen if the host gets
                # changed after the initial connection was established. E.g.:
                #   * the client offers http/1.1 and h2,
                #   * the initial host is only capable of http/1.1,
                #   * then the first server connection negotiates http/1.1,
                #   * but after the server_conn change, the new host offers h2
                #   * which results in garbage because the layers don' match.
                alpn = [self.client_conn.get_alpn_proto_negotiated()]

            # We pass through the list of ciphers send by the client, because some HTTP/2 servers
            # will select a non-HTTP/2 compatible cipher from our default list and then hang up
            # because it's incompatible with h2. :-)
            ciphers_server = self.config.options.ciphers_server
            if not ciphers_server and self._client_tls:
                ciphers_server = []
                for id in self._client_hello.cipher_suites:
                    if id in CIPHER_ID_NAME_MAP.keys():
                        ciphers_server.append(CIPHER_ID_NAME_MAP[id])
                ciphers_server = ':'.join(ciphers_server)

            args = net_tls.client_arguments_from_options(self.config.options)
            args["cipher_list"] = ciphers_server
            self.server_conn.establish_tls(
                sni=self.server_sni,
                alpn_protos=alpn,
                **args
            )
            tls_cert_err = self.server_conn.ssl_verification_error
            if tls_cert_err is not None:
                self.log(str(tls_cert_err), "warn")
                self.log("Ignoring server verification error, continuing with connection", "warn")
        except exceptions.InvalidCertificateException as e:
            raise exceptions.InvalidServerCertificate(str(e))
        except exceptions.TlsException as e:
            raise exceptions.TlsProtocolException(
                "Cannot establish TLS with {host}:{port} (sni: {sni}): {e}".format(
                    host=self.server_conn.address[0],
                    port=self.server_conn.address[1],
                    sni=self.server_sni,
                    e=repr(e)
                )
            )

        proto = self.alpn_for_client_connection.decode() if self.alpn_for_client_connection else '-'
        self.log("ALPN selected by server: {}".format(proto), "debug")

    def _find_cert(self):
        """
        This function determines the Common Name (CN), Subject Alternative Names (SANs) and Organization Name
        our certificate should have and then fetches a matching cert from the certstore.
        """
        host = None
        sans = set()
        organization = None

        # In normal operation, the server address should always be known at this point.
        # However, we may just want to establish TLS so that we can send an error message to the client,
        # in which case the address can be None.
        if self.server_conn.address:
            host = self.server_conn.address[0].encode("idna")

        # Should we incorporate information from the server certificate?
        use_upstream_cert = (
            self.server_conn and
            self.server_conn.tls_established and
            self.config.options.upstream_cert
        )
        if use_upstream_cert:
            upstream_cert = self.server_conn.cert
            sans.update(upstream_cert.altnames)
            if upstream_cert.cn:
                sans.add(host)
                host = upstream_cert.cn.decode("utf8").encode("idna")
            if upstream_cert.organization:
                organization = upstream_cert.organization
        # Also add SNI values.
        if self._client_hello.sni:
            sans.add(self._client_hello.sni)
        if self._custom_server_sni:
            sans.add(self._custom_server_sni.encode("idna"))

        # RFC 2818: If a subjectAltName extension of type dNSName is present, that MUST be used as the identity.
        # In other words, the Common Name is irrelevant then.
        if host:
            sans.add(host)
        return self.config.certstore.get_cert(host, list(sans), organization)
