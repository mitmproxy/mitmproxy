# To enable all SSL methods use: SSLv23
# then add options to disable certain methods
# https://bugs.launchpad.net/pyopenssl/+bug/1020632/comments/3
import binascii
import io
import os
import struct
import threading
import typing

import certifi
from OpenSSL import SSL
from kaitaistruct import KaitaiStream

import mitmproxy.options
from mitmproxy import certs, exceptions
from mitmproxy.contrib.kaitaistruct import tls_client_hello
from mitmproxy.net import check

BASIC_OPTIONS = (
    SSL.OP_CIPHER_SERVER_PREFERENCE
)
if hasattr(SSL, "OP_NO_COMPRESSION"):
    BASIC_OPTIONS |= SSL.OP_NO_COMPRESSION

DEFAULT_METHOD = SSL.SSLv23_METHOD
DEFAULT_OPTIONS = (
    SSL.OP_NO_SSLv2 |
    SSL.OP_NO_SSLv3 |
    BASIC_OPTIONS
)

"""
Map a reasonable SSL version specification into the format OpenSSL expects.
Don't ask...
https://bugs.launchpad.net/pyopenssl/+bug/1020632/comments/3
"""
VERSION_CHOICES = {
    "all": (SSL.SSLv23_METHOD, BASIC_OPTIONS),
    # SSLv23_METHOD + NO_SSLv2 + NO_SSLv3 == TLS 1.0+
    # TLSv1_METHOD would be TLS 1.0 only
    "secure": (DEFAULT_METHOD, DEFAULT_OPTIONS),
    "SSLv2": (SSL.SSLv2_METHOD, BASIC_OPTIONS),
    "SSLv3": (SSL.SSLv3_METHOD, BASIC_OPTIONS),
    "TLSv1": (SSL.TLSv1_METHOD, BASIC_OPTIONS),
    "TLSv1_1": (SSL.TLSv1_1_METHOD, BASIC_OPTIONS),
    "TLSv1_2": (SSL.TLSv1_2_METHOD, BASIC_OPTIONS),
}

METHOD_NAMES = {
    SSL.SSLv2_METHOD: "SSLv2",
    SSL.SSLv3_METHOD: "SSLv3",
    SSL.SSLv23_METHOD: "SSLv23",
    SSL.TLSv1_METHOD: "TLSv1",
    SSL.TLSv1_1_METHOD: "TLSv1.1",
    SSL.TLSv1_2_METHOD: "TLSv1.2",
}


def client_arguments_from_options(options: "mitmproxy.options.Options") -> dict:

    if options.ssl_insecure:
        verify = SSL.VERIFY_NONE
    else:
        verify = SSL.VERIFY_PEER

    method, tls_options = VERSION_CHOICES[options.ssl_version_server]

    return {
        "verify": verify,
        "method": method,
        "options": tls_options,
        "ca_path": options.ssl_verify_upstream_trusted_confdir,
        "ca_pemfile": options.ssl_verify_upstream_trusted_ca,
        "client_certs": options.client_certs,
        "cipher_list": options.ciphers_server,
    }


class MasterSecretLogger:
    def __init__(self, filename):
        self.filename = filename
        self.f = None
        self.lock = threading.Lock()

    # required for functools.wraps, which pyOpenSSL uses.
    __name__ = "MasterSecretLogger"

    def __call__(self, connection, where, ret):
        done_now = (
            where == SSL.SSL_CB_HANDSHAKE_DONE and ret == 1
        )
        # this is a horrendous workaround for https://github.com/mitmproxy/mitmproxy/pull/3692#issuecomment-608454530:
        # OpenSSL 1.1.1f decided to not make connection.master_key() fail in the SSL_CB_HANDSHAKE_DONE callback.
        # To support various OpenSSL versions and still log master secrets, we now mark connections where this has
        # happened and then try again on the next event. This is ugly and shouldn't be done, but eventually we
        # replace this with context.set_keylog_callback anyways.
        done_previously_but_not_logged_yet = (
            hasattr(connection, "_still_needs_masterkey")
        )
        if done_now or done_previously_but_not_logged_yet:
            with self.lock:
                if not self.f:
                    d = os.path.dirname(self.filename)
                    if not os.path.isdir(d):
                        os.makedirs(d)
                    self.f = open(self.filename, "ab")
                    self.f.write(b"\r\n")
                try:
                    client_random = binascii.hexlify(connection.client_random())
                    masterkey = binascii.hexlify(connection.master_key())
                except (AssertionError, SSL.Error):  # careful: exception type changes between pyOpenSSL versions
                    connection._still_needs_masterkey = True
                else:
                    self.f.write(b"CLIENT_RANDOM %s %s\r\n" % (client_random, masterkey))
                    self.f.flush()
                    if hasattr(connection, "_still_needs_masterkey"):
                        delattr(connection, "_still_needs_masterkey")

    def close(self):
        with self.lock:
            if self.f:
                self.f.close()

    @staticmethod
    def create_logfun(filename):
        if filename:
            return MasterSecretLogger(filename)
        return None


log_master_secret = MasterSecretLogger.create_logfun(
    os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")
)


def _create_ssl_context(
        method: int = DEFAULT_METHOD,
        options: int = DEFAULT_OPTIONS,
        ca_path: str = None,
        ca_pemfile: str = None,
        cipher_list: str = None,
        alpn_protos: typing.Iterable[bytes] = None,
        alpn_select=None,
        alpn_select_callback: typing.Callable[[typing.Any, typing.Any], bytes] = None,
        verify: int = SSL.VERIFY_PEER,
        verify_callback: typing.Optional[
            typing.Callable[[SSL.Connection, SSL.X509, int, int, bool], bool]
        ] = None,
) -> SSL.Context:
    """
    Creates an SSL Context.

    :param method: One of SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD, TLSv1_1_METHOD, or TLSv1_2_METHOD
    :param options: A bit field consisting of OpenSSL.SSL.OP_* values
    :param verify: A bit field consisting of OpenSSL.SSL.VERIFY_* values
    :param ca_path: Path to a directory of trusted CA certificates prepared using the c_rehash tool
    :param ca_pemfile: Path to a PEM formatted trusted CA certificate
    :param cipher_list: A textual OpenSSL cipher list, see https://www.openssl.org/docs/apps/ciphers.html
    :rtype : SSL.Context
    """
    try:
        context = SSL.Context(method)
    except ValueError:
        method_name = METHOD_NAMES.get(method, "unknown")
        raise exceptions.TlsException(
            "SSL method \"%s\" is most likely not supported "
            "or disabled (for security reasons) in your libssl. "
            "Please refer to https://github.com/mitmproxy/mitmproxy/issues/1101 "
            "for more details." % method_name
        )

    # Options (NO_SSLv2/3)
    if options is not None:
        context.set_options(options)

    # Verify Options (NONE/PEER and trusted CAs)
    if verify is not None:
        context.set_verify(verify, verify_callback)
        if ca_path is None and ca_pemfile is None:
            ca_pemfile = certifi.where()
        try:
            context.load_verify_locations(ca_pemfile, ca_path)
        except SSL.Error:
            raise exceptions.TlsException(
                "Cannot load trusted certificates ({}, {}).".format(
                    ca_pemfile, ca_path
                )
            )

    # Workaround for
    # https://github.com/pyca/pyopenssl/issues/190
    # https://github.com/mitmproxy/mitmproxy/issues/472
    # Options already set before are not cleared.
    context.set_mode(SSL._lib.SSL_MODE_AUTO_RETRY)

    # Cipher List
    if cipher_list:
        try:
            context.set_cipher_list(cipher_list.encode())
        except SSL.Error as v:
            raise exceptions.TlsException("SSL cipher specification error: %s" % str(v))

    # SSLKEYLOGFILE
    if log_master_secret:
        context.set_info_callback(log_master_secret)

    if alpn_protos is not None:
        # advertise application layer protocols
        context.set_alpn_protos(alpn_protos)
    elif alpn_select is not None and alpn_select_callback is None:
        # select application layer protocol
        def alpn_select_callback(conn_, options):
            if alpn_select in options:
                return bytes(alpn_select)
            else:  # pragma: no cover
                return options[0]

        context.set_alpn_select_callback(alpn_select_callback)
    elif alpn_select_callback is not None and alpn_select is None:
        if not callable(alpn_select_callback):
            raise exceptions.TlsException("ALPN error: alpn_select_callback must be a function.")
        context.set_alpn_select_callback(alpn_select_callback)
    elif alpn_select_callback is not None and alpn_select is not None:
        raise exceptions.TlsException(
            "ALPN error: only define alpn_select (string) OR alpn_select_callback (function).")

    return context


def create_client_context(
        cert: str = None,
        sni: str = None,
        address: str = None,
        verify: int = SSL.VERIFY_NONE,
        **sslctx_kwargs
) -> SSL.Context:
    """
    Args:
        cert: Path to a file containing both client cert and private key.
        sni: Server Name Indication. Required for VERIFY_PEER
        address: server address, used for expressive error messages only
        verify: A bit field consisting of OpenSSL.SSL.VERIFY_* values
    """

    if sni is None and verify != SSL.VERIFY_NONE:
        raise exceptions.TlsException("Cannot validate certificate hostname without SNI")

    def verify_callback(
            conn: SSL.Connection,
            x509: SSL.X509,
            errno: int,
            depth: int,
            is_cert_verified: bool
    ) -> bool:
        if is_cert_verified and depth == 0 and not sni:
            conn.cert_error = exceptions.InvalidCertificateException(
                f"Certificate verification error for {address}: Cannot validate hostname, SNI missing."
            )
            is_cert_verified = False
        elif is_cert_verified:
            pass
        else:
            conn.cert_error = exceptions.InvalidCertificateException(
                "Certificate verification error for {}: {} (errno: {}, depth: {})".format(
                    sni,
                    SSL._ffi.string(SSL._lib.X509_verify_cert_error_string(errno)).decode(),
                    errno,
                    depth
                )
            )

        # SSL_VERIFY_NONE: The handshake will be continued regardless of the verification result.
        return is_cert_verified

    context = _create_ssl_context(
        verify=verify,
        verify_callback=verify_callback,
        **sslctx_kwargs,
    )

    if sni:
        # Manually enable hostname verification on the context object.
        # https://wiki.openssl.org/index.php/Hostname_validation
        param = SSL._lib.SSL_CTX_get0_param(context._context)
        # Matching on the CN is disabled in both Chrome and Firefox, so we disable it, too.
        # https://www.chromestatus.com/feature/4981025180483584
        SSL._lib.X509_VERIFY_PARAM_set_hostflags(
            param,
            SSL._lib.X509_CHECK_FLAG_NO_PARTIAL_WILDCARDS | SSL._lib.X509_CHECK_FLAG_NEVER_CHECK_SUBJECT
        )
        SSL._openssl_assert(
            SSL._lib.X509_VERIFY_PARAM_set1_host(param, sni.encode("idna"), 0) == 1
        )

    # Client Certs
    if cert:
        try:
            context.use_privatekey_file(cert)
            context.use_certificate_chain_file(cert)
        except SSL.Error as v:
            raise exceptions.TlsException("SSL client certificate error: %s" % str(v))
    return context


def accept_all(
        conn_: SSL.Connection,
        x509: SSL.X509,
        errno: int,
        err_depth: int,
        is_cert_verified: bool,
) -> bool:
    # Return true to prevent cert verification error
    return True


def create_server_context(
        cert: typing.Union[certs.Cert, str],
        key: SSL.PKey,
        handle_sni: typing.Optional[typing.Callable[[SSL.Connection], None]] = None,
        request_client_cert: bool = False,
        chain_file=None,
        dhparams=None,
        extra_chain_certs: typing.Iterable[certs.Cert] = None,
        **sslctx_kwargs
) -> SSL.Context:
    """
        cert: A certs.Cert object or the path to a certificate
        chain file.

        handle_sni: SNI handler, should take a connection object. Server
        name can be retrieved like this:

                connection.get_servername()

        The request_client_cert argument requires some explanation. We're
        supposed to be able to do this with no negative effects - if the
        client has no cert to present, we're notified and proceed as usual.
        Unfortunately, Android seems to have a bug (tested on 4.2.2) - when
        an Android client is asked to present a certificate it does not
        have, it hangs up, which is frankly bogus. Some time down the track
        we may be able to make the proper behaviour the default again, but
        until then we're conservative.
    """

    if request_client_cert:
        verify = SSL.VERIFY_PEER
    else:
        verify = SSL.VERIFY_NONE

    context = _create_ssl_context(
        ca_pemfile=chain_file,
        verify=verify,
        verify_callback=accept_all,
        **sslctx_kwargs,
    )

    context.use_privatekey(key)
    if isinstance(cert, certs.Cert):
        context.use_certificate(cert.x509)
    else:
        context.use_certificate_chain_file(cert)

    if extra_chain_certs:
        for i in extra_chain_certs:
            context.add_extra_chain_cert(i.x509)

    if handle_sni:
        # SNI callback happens during do_handshake()
        context.set_tlsext_servername_callback(handle_sni)

    if dhparams:
        SSL._lib.SSL_CTX_set_tmp_dh(context._context, dhparams)

    return context


def is_tls_record_magic(d):
    """
    Returns:
        True, if the passed bytes start with the TLS record magic bytes.
        False, otherwise.
    """
    d = d[:3]

    # TLS ClientHello magic, works for SSLv3, TLSv1.0, TLSv1.1, TLSv1.2
    # http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
    return (
        len(d) == 3 and
        d[0] == 0x16 and
        d[1] == 0x03 and
        0x0 <= d[2] <= 0x03
    )


def get_client_hello(rfile):
    """
    Peek into the socket and read all records that contain the initial client hello message.

    client_conn:
        The :py:class:`client connection <mitmproxy.connections.ClientConnection>`.

    Returns:
        The raw handshake packet bytes, without TLS record header(s).
    """
    client_hello = b""
    client_hello_size = 1
    offset = 0
    while len(client_hello) < client_hello_size:
        record_header = rfile.peek(offset + 5)[offset:]
        if not is_tls_record_magic(record_header) or len(record_header) < 5:
            raise exceptions.TlsProtocolException(
                'Expected TLS record, got "%s" instead.' % record_header)
        record_size = struct.unpack_from("!H", record_header, 3)[0] + 5
        record_body = rfile.peek(offset + record_size)[offset + 5:]
        if len(record_body) != record_size - 5:
            raise exceptions.TlsProtocolException(
                "Unexpected EOF in TLS handshake: %s" % record_body)
        client_hello += record_body
        offset += record_size
        client_hello_size = struct.unpack("!I", b'\x00' + client_hello[1:4])[0] + 4
    return client_hello


class ClientHello:

    def __init__(self, raw_client_hello):
        self._client_hello = tls_client_hello.TlsClientHello(
            KaitaiStream(io.BytesIO(raw_client_hello))
        )

    @property
    def cipher_suites(self):
        return self._client_hello.cipher_suites.cipher_suites

    @property
    def sni(self) -> typing.Optional[bytes]:
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                is_valid_sni_extension = (
                    extension.type == 0x00 and
                    len(extension.body.server_names) == 1 and
                    extension.body.server_names[0].name_type == 0 and
                    check.is_valid_host(extension.body.server_names[0].host_name)
                )
                if is_valid_sni_extension:
                    return extension.body.server_names[0].host_name
        return None

    @property
    def alpn_protocols(self):
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                if extension.type == 0x10:
                    return list(x.name for x in extension.body.alpn_protocols)
        return []

    @property
    def extensions(self) -> typing.List[typing.Tuple[int, bytes]]:
        ret = []
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                body = getattr(extension, "_raw_body", extension.body)
                ret.append((extension.type, body))
        return ret

    @classmethod
    def from_file(cls, client_conn) -> "ClientHello":
        """
        Peek into the connection, read the initial client hello and parse it to obtain ALPN values.
        client_conn:
            The :py:class:`client connection <mitmproxy.connections.ClientConnection>`.
        Returns:
            :py:class:`client hello <mitmproxy.net.tls.ClientHello>`.
        """
        try:
            raw_client_hello = get_client_hello(client_conn)[4:]  # exclude handshake header.
        except exceptions.ProtocolException as e:
            raise exceptions.TlsProtocolException('Cannot read raw Client Hello: %s' % repr(e))

        try:
            return cls(raw_client_hello)
        except EOFError as e:
            raise exceptions.TlsProtocolException(
                f"Cannot parse Client Hello: {e!r}, Raw Client Hello: {binascii.hexlify(raw_client_hello)!r}"
            )

    def __repr__(self):
        return f"ClientHello(sni: {self.sni}, alpn_protocols: {self.alpn_protocols})"
