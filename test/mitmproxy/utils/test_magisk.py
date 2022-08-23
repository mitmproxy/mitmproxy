import pytest
from mitmproxy.utils import magisk
from cryptography import x509
from mitmproxy.test import taddons
import os
import subprocess
import shutil


def test_get_ca(tdata):
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        assert isinstance(ca, x509.Certificate)


@pytest.mark.skipif(
    shutil.which("openssl") is None, reason="openssl not avalible as executable."
)
def test_subject_hash_old(tdata):
    # checks if the hash is the same as that comming form openssl
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        our_hash = magisk.subject_hash_old(ca)

        confdir = tctx.options.confdir
        pemfile = os.path.join(confdir, "mitmproxy-ca-cert.pem")
        openssl_result = subprocess.run(
            ["openssl", "x509", "-in", pemfile, "-subject_hash_old"],
            capture_output=True,
        )
        openssl_hash = openssl_result.stdout.decode().strip().split("\n")[0]
        assert openssl_hash == our_hash


def test_magisk_write(tdata, tmp_path):
    # checks if the hash is the same as that comming form openssl
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        magisk_path = tmp_path / "mitmproxy-magisk-module.zip"
        magisk.write_magisk_module(magisk_path)

        assert os.path.exists(magisk_path)
