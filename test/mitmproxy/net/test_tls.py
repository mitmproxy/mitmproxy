from pathlib import Path

from OpenSSL import SSL, crypto
from mitmproxy import certs
from mitmproxy.net import tls


def test_make_master_secret_logger():
    assert tls.make_master_secret_logger(None) is None
    assert isinstance(tls.make_master_secret_logger("filepath"), tls.MasterSecretLogger)


def test_sslkeylogfile(tdata, monkeypatch):
    keylog = []
    monkeypatch.setattr(
        tls, "log_master_secret", lambda conn, secrets: keylog.append(secrets)
    )

    store = certs.CertStore.from_files(
        Path(tdata.path("mitmproxy/net/data/verificationcerts/trusted-root.pem")),
        Path(tdata.path("mitmproxy/net/data/dhparam.pem")),
    )
    entry = store.get_cert("example.com", [], None)

    cctx = tls.create_proxy_server_context(
        method=tls.Method.TLS_CLIENT_METHOD,
        min_version=tls.DEFAULT_MIN_VERSION,
        max_version=tls.DEFAULT_MAX_VERSION,
        cipher_list=None,
        verify=tls.Verify.VERIFY_NONE,
        ca_path=None,
        ca_pemfile=None,
        client_cert=None,
    )
    sctx = tls.create_client_proxy_context(
        method=tls.Method.TLS_SERVER_METHOD,
        min_version=tls.DEFAULT_MIN_VERSION,
        max_version=tls.DEFAULT_MAX_VERSION,
        cipher_list=None,
        chain_file=entry.chain_file,
        alpn_select_callback=None,
        request_client_cert=False,
        extra_chain_certs=(),
        dhparams=store.dhparams,
    )

    server = SSL.Connection(sctx)
    server.set_accept_state()

    server.use_certificate(entry.cert.to_pyopenssl())
    server.use_privatekey(crypto.PKey.from_cryptography_key(entry.privatekey))

    client = SSL.Connection(cctx)
    client.set_connect_state()

    read, write = client, server
    while True:
        try:
            read.do_handshake()
        except SSL.WantReadError:
            write.bio_write(read.bio_read(2 ** 16))
        else:
            break
        read, write = write, read

    assert keylog
    assert keylog[0].startswith(b"SERVER_HANDSHAKE_TRAFFIC_SECRET")


def test_is_record_magic():
    assert not tls.is_tls_record_magic(b"POST /")
    assert not tls.is_tls_record_magic(b"\x16\x03")
    assert not tls.is_tls_record_magic(b"\x16\x03\x04")
    assert tls.is_tls_record_magic(b"\x16\x03\x00")
    assert tls.is_tls_record_magic(b"\x16\x03\x01")
    assert tls.is_tls_record_magic(b"\x16\x03\x02")
    assert tls.is_tls_record_magic(b"\x16\x03\x03")
