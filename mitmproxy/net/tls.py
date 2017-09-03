# To enable all SSL methods use: SSLv23
# then add options to disable certain methods
# https://bugs.launchpad.net/pyopenssl/+bug/1020632/comments/3
import binascii
import os
import threading
import typing

import certifi
from OpenSSL import SSL

from mitmproxy import exceptions, certs

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


class MasterSecretLogger:
    def __init__(self, filename):
        self.filename = filename
        self.f = None
        self.lock = threading.Lock()

    # required for functools.wraps, which pyOpenSSL uses.
    __name__ = "MasterSecretLogger"

    def __call__(self, connection, where, ret):
        if where == SSL.SSL_CB_HANDSHAKE_DONE and ret == 1:
            with self.lock:
                if not self.f:
                    d = os.path.dirname(self.filename)
                    if not os.path.isdir(d):
                        os.makedirs(d)
                    self.f = open(self.filename, "ab")
                    self.f.write(b"\r\n")
                client_random = binascii.hexlify(connection.client_random())
                masterkey = binascii.hexlify(connection.master_key())
                self.f.write(b"CLIENT_RANDOM %s %s\r\n" % (client_random, masterkey))
                self.f.flush()

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
        verify_options: int = SSL.VERIFY_NONE,
        ca_path: str = None,
        ca_pemfile: str = None,
        cipher_list: str = None,
        alpn_protos: typing.Iterable[bytes] = None,
        alpn_select=None,
        alpn_select_callback: typing.Callable[[typing.Any, typing.Any], bytes] = None,
        sni=None,
        verify_error_callback: typing.Callable[
            [exceptions.InvalidCertificateException], None] = None,
) -> SSL.Context:
    """
    Creates an SSL Context.

    :param method: One of SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, TLSv1_METHOD, TLSv1_1_METHOD, or TLSv1_2_METHOD
    :param options: A bit field consisting of OpenSSL.SSL.OP_* values
    :param verify_options: A bit field consisting of OpenSSL.SSL.VERIFY_* values
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
    if verify_options is not None:
        def verify_cert(conn, x509, errno, err_depth, is_cert_verified):
            if not is_cert_verified:
                if verify_error_callback:
                    e = exceptions.InvalidCertificateException(
                        "Certificate Verification Error for {}: {} (errno: {}, depth: {})".format(
                            sni,
                            SSL._ffi.string(SSL._lib.X509_verify_cert_error_string(errno)).decode(),
                            errno,
                            err_depth
                        )
                    )
                    verify_error_callback(e)
            return is_cert_verified

        context.set_verify(verify_options, verify_cert)
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
        **sslctx_kwargs
) -> SSL.Context:
    context = _create_ssl_context(
        **sslctx_kwargs
    )
    # Client Certs
    if cert:
        try:
            context.use_privatekey_file(cert)
            context.use_certificate_file(cert)
        except SSL.Error as v:
            raise exceptions.TlsException("SSL client certificate error: %s" % str(v))
    return context


def create_server_context(
        cert: typing.Union[certs.SSLCert, str],
        key: SSL.PKey,
        handle_sni: typing.Optional[typing.Callable[[SSL.Connection], None]] = None,
        request_client_cert: typing.Optional[typing.Callable[[certs.SSLCert], None]] = None,
        chain_file=None,
        dhparams=None,
        extra_chain_certs: typing.Iterable[certs.SSLCert] = None,
        **sslctx_kwargs
) -> SSL.Context:
    """
        cert: A certs.SSLCert object or the path to a certificate
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

    context = _create_ssl_context(ca_pemfile=chain_file, **sslctx_kwargs)

    context.use_privatekey(key)
    if isinstance(cert, certs.SSLCert):
        context.use_certificate(cert.x509)
    else:
        context.use_certificate_chain_file(cert)

    if extra_chain_certs:
        for i in extra_chain_certs:
            context.add_extra_chain_cert(i.x509)

    if handle_sni:
        # SNI callback happens during do_handshake()
        context.set_tlsext_servername_callback(handle_sni)

    if request_client_cert:
        def save_cert(conn_, x509, errno_, depth_, preverify_ok_):
            cert = certs.SSLCert(x509)
            request_client_cert(cert)
            # Return true to prevent cert verification error
            return True

        context.set_verify(SSL.VERIFY_PEER, save_cert)

    if dhparams:
        SSL._lib.SSL_CTX_set_tmp_dh(context._context, dhparams)

    return context
