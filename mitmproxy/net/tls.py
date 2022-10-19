import os
import threading
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Optional

import certifi

from OpenSSL.crypto import X509

from OpenSSL import SSL
from mitmproxy import certs


# redeclared here for strict type checking
class Method(Enum):
    TLS_SERVER_METHOD = SSL.TLS_SERVER_METHOD
    TLS_CLIENT_METHOD = SSL.TLS_CLIENT_METHOD
    # Type-pyopenssl does not know about these DTLS constants.
    DTLS_SERVER_METHOD = SSL.DTLS_SERVER_METHOD   # type: ignore
    DTLS_CLIENT_METHOD = SSL.DTLS_CLIENT_METHOD   # type: ignore


try:
    SSL._lib.TLS_server_method  # type: ignore
except AttributeError as e:  # pragma: no cover
    raise RuntimeError(
        "Your installation of the cryptography Python package is outdated."
    ) from e


class Version(Enum):
    UNBOUNDED = 0
    SSL3 = SSL.SSL3_VERSION
    TLS1 = SSL.TLS1_VERSION
    TLS1_1 = SSL.TLS1_1_VERSION
    TLS1_2 = SSL.TLS1_2_VERSION
    TLS1_3 = SSL.TLS1_3_VERSION


class Verify(Enum):
    VERIFY_NONE = SSL.VERIFY_NONE
    VERIFY_PEER = SSL.VERIFY_PEER


DEFAULT_MIN_VERSION = Version.TLS1_2
DEFAULT_MAX_VERSION = Version.UNBOUNDED
DEFAULT_OPTIONS = SSL.OP_CIPHER_SERVER_PREFERENCE | SSL.OP_NO_COMPRESSION


class MasterSecretLogger:
    def __init__(self, filename: Path):
        self.filename = filename.expanduser()
        self.f: Optional[BinaryIO] = None
        self.lock = threading.Lock()

    # required for functools.wraps, which pyOpenSSL uses.
    __name__ = "MasterSecretLogger"

    def __call__(self, connection: SSL.Connection, keymaterial: bytes) -> None:
        with self.lock:
            if self.f is None:
                self.filename.parent.mkdir(parents=True, exist_ok=True)
                self.f = self.filename.open("ab")
                self.f.write(b"\n")
            self.f.write(keymaterial + b"\n")
            self.f.flush()

    def close(self):
        with self.lock:
            if self.f is not None:
                self.f.close()


def make_master_secret_logger(filename: Optional[str]) -> Optional[MasterSecretLogger]:
    if filename:
        return MasterSecretLogger(Path(filename))
    return None


log_master_secret = make_master_secret_logger(
    os.getenv("MITMPROXY_SSLKEYLOGFILE") or os.getenv("SSLKEYLOGFILE")
)


def _create_ssl_context(
    *,
    method: Method,
    min_version: Version,
    max_version: Version,
    cipher_list: Optional[Iterable[str]],
) -> SSL.Context:
    context = SSL.Context(method.value)

    ok = SSL._lib.SSL_CTX_set_min_proto_version(context._context, min_version.value)  # type: ignore
    ok += SSL._lib.SSL_CTX_set_max_proto_version(context._context, max_version.value)  # type: ignore
    if ok != 2:
        raise RuntimeError(
            f"Error setting TLS versions ({min_version=}, {max_version=}). "
            "The version you specified may be unavailable in your libssl."
        )

    # Options
    context.set_options(DEFAULT_OPTIONS)

    # Cipher List
    if cipher_list is not None:
        try:
            context.set_cipher_list(b":".join(x.encode() for x in cipher_list))
        except SSL.Error as e:
            raise RuntimeError(f"SSL cipher specification error: {e}") from e

    # SSLKEYLOGFILE
    if log_master_secret:
        context.set_keylog_callback(log_master_secret)

    return context


@lru_cache(256)
def create_proxy_server_context(
    *,
    method: Method,
    min_version: Version,
    max_version: Version,
    cipher_list: Optional[tuple[str, ...]],
    verify: Verify,
    ca_path: Optional[str],
    ca_pemfile: Optional[str],
    client_cert: Optional[str],
) -> SSL.Context:
    context: SSL.Context = _create_ssl_context(
        method=method,
        min_version=min_version,
        max_version=max_version,
        cipher_list=cipher_list,
    )
    context.set_verify(verify.value, None)

    if ca_path is None and ca_pemfile is None:
        ca_pemfile = certifi.where()
    try:
        context.load_verify_locations(ca_pemfile, ca_path)
    except SSL.Error as e:
        raise RuntimeError(
            f"Cannot load trusted certificates ({ca_pemfile=}, {ca_path=})."
        ) from e

    # Client Certs
    if client_cert:
        try:
            context.use_privatekey_file(client_cert)
            context.use_certificate_chain_file(client_cert)
        except SSL.Error as e:
            raise RuntimeError(f"Cannot load TLS client certificate: {e}") from e

    return context


@lru_cache(256)
def create_client_proxy_context(
    *,
    method: Method,
    min_version: Version,
    max_version: Version,
    cipher_list: Optional[tuple[str, ...]],
    chain_file: Optional[Path],
    alpn_select_callback: Optional[Callable[[SSL.Connection, list[bytes]], Any]],
    request_client_cert: bool,
    extra_chain_certs: tuple[certs.Cert, ...],
    dhparams: certs.DHParams,
) -> SSL.Context:
    context: SSL.Context = _create_ssl_context(
        method=method,
        min_version=min_version,
        max_version=max_version,
        cipher_list=cipher_list,
    )

    if chain_file is not None:
        try:
            context.load_verify_locations(str(chain_file), None)
        except SSL.Error as e:
            raise RuntimeError(f"Cannot load certificate chain ({chain_file}).") from e

    if alpn_select_callback is not None:
        assert callable(alpn_select_callback)
        context.set_alpn_select_callback(alpn_select_callback)

    if request_client_cert:
        # The request_client_cert argument requires some explanation. We're
        # supposed to be able to do this with no negative effects - if the
        # client has no cert to present, we're notified and proceed as usual.
        # Unfortunately, Android seems to have a bug (tested on 4.2.2) - when
        # an Android client is asked to present a certificate it does not
        # have, it hangs up, which is frankly bogus. Some time down the track
        # we may be able to make the proper behaviour the default again, but
        # until then we're conservative.
        context.set_verify(Verify.VERIFY_PEER.value, accept_all)
    else:
        context.set_verify(Verify.VERIFY_NONE.value, None)

    for i in extra_chain_certs:
        context.add_extra_chain_cert(i.to_pyopenssl())

    if dhparams:
        res = SSL._lib.SSL_CTX_set_tmp_dh(context._context, dhparams)  # type: ignore
        SSL._openssl_assert(res == 1)  # type: ignore

    return context


def accept_all(
    conn_: SSL.Connection,
    x509: X509,
    errno: int,
    err_depth: int,
    is_cert_verified: int,
) -> bool:
    # Return true to prevent cert verification error
    return True


def is_tls_record_magic(d):
    """
    Returns:
        True, if the passed bytes start with the TLS record magic bytes.
        False, otherwise.
    """
    d = d[:3]

    # TLS ClientHello magic, works for SSLv3, TLSv1.0, TLSv1.1, TLSv1.2, and TLSv1.3
    # http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
    # https://tls13.ulfheim.net/
    return len(d) == 3 and d[0] == 0x16 and d[1] == 0x03 and 0x0 <= d[2] <= 0x03
