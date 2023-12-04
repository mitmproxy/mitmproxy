from cryptography import x509

from mitmproxy.test import taddons
from mitmproxy.utils import magisk


def test_get_ca_confdir(tdata):
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        assert isinstance(ca, x509.Certificate)


def test_get_ca_certstore(tdata):
    with taddons.context() as tctx:
        tctx.options.certstore = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        assert isinstance(ca, x509.Certificate)


def test_get_ca_confdir_certstore(tdata, tmp_path):
    with taddons.context() as tctx:
        confdir = tmp_path / 'confdir'
        tctx.options.confdir = str(confdir)
        tctx.options.certstore = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        assert not confdir.exists()
        assert isinstance(ca, x509.Certificate)


def test_subject_hash_old(tdata):
    # checks if the hash is the same as that comming form openssl
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        ca = magisk.get_ca_from_files()
        our_hash = magisk.subject_hash_old(ca)
        assert our_hash == "efb15d7d"


def test_magisk_write(tdata, tmp_path):
    # checks if the hash is the same as that comming form openssl
    with taddons.context() as tctx:
        tctx.options.confdir = tdata.path("mitmproxy/data/confdir")
        magisk_path = tmp_path / "mitmproxy-magisk-module.zip"
        magisk.write_magisk_module(magisk_path)

        assert magisk_path.exists()
