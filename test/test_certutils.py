import os
from netlib import certutils
import tutils


class TestCertStore:
    def test_create_explicit(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            assert ca.get_cert("foo", [])

            ca2 = certutils.CertStore.from_store(d, "test")
            assert ca2.get_cert("foo", [])

            assert ca.cert.get_serial_number() == ca2.cert.get_serial_number()

    def test_create_tmp(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            assert ca.get_cert("foo.com", [])
            assert ca.get_cert("foo.com", [])
            assert ca.get_cert("*.foo.com", [])


class TestDummyCert:
    def test_with_ca(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            r = certutils.dummy_cert(
                ca.pkey,
                ca.cert,
                "foo.com",
                ["one.com", "two.com", "*.three.com"]
            )
            assert r.cn == "foo.com"


class TestSSLCert:
    def test_simple(self):
        c = certutils.SSLCert.from_pem(file(tutils.test_data.path("data/text_cert"), "rb").read())
        assert c.cn == "google.com"
        assert len(c.altnames) == 436

        c = certutils.SSLCert.from_pem(file(tutils.test_data.path("data/text_cert_2"), "rb").read())
        assert c.cn == "www.inode.co.nz"
        assert len(c.altnames) == 2
        assert c.digest("sha1")
        assert c.notbefore
        assert c.notafter
        assert c.subject
        assert c.keyinfo == ("RSA", 2048)
        assert c.serial
        assert c.issuer
        assert c.to_pem()
        c.has_expired

    def test_err_broken_sans(self):
        c = certutils.SSLCert.from_pem(file(tutils.test_data.path("data/text_cert_weird1"), "rb").read())
        # This breaks unless we ignore a decoding error.
        c.altnames

    def test_der(self):
        d = file(tutils.test_data.path("data/dercert"),"rb").read()
        s = certutils.SSLCert.from_der(d)
        assert s.cn
