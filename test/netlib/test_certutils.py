import os
from netlib import certutils, tutils

# class TestDNTree:
#     def test_simple(self):
#         d = certutils.DNTree()
#         d.add("foo.com", "foo")
#         d.add("bar.com", "bar")
#         assert d.get("foo.com") == "foo"
#         assert d.get("bar.com") == "bar"
#         assert not d.get("oink.com")
#         assert not d.get("oink")
#         assert not d.get("")
#         assert not d.get("oink.oink")
#
#         d.add("*.match.org", "match")
#         assert not d.get("match.org")
#         assert d.get("foo.match.org") == "match"
#         assert d.get("foo.foo.match.org") == "match"
#
#     def test_wildcard(self):
#         d = certutils.DNTree()
#         d.add("foo.com", "foo")
#         assert not d.get("*.foo.com")
#         d.add("*.foo.com", "wild")
#
#         d = certutils.DNTree()
#         d.add("*", "foo")
#         assert d.get("foo.com") == "foo"
#         assert d.get("*.foo.com") == "foo"
#         assert d.get("com") == "foo"


class TestCertStore:

    def test_create_explicit(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            assert ca.get_cert(b"foo", [])

            ca2 = certutils.CertStore.from_store(d, "test")
            assert ca2.get_cert(b"foo", [])

            assert ca.default_ca.get_serial_number() == ca2.default_ca.get_serial_number()

    def test_create_no_common_name(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            assert ca.get_cert(None, [])[0].cn is None

    def test_create_tmp(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            assert ca.get_cert(b"foo.com", [])
            assert ca.get_cert(b"foo.com", [])
            assert ca.get_cert(b"*.foo.com", [])

            r = ca.get_cert(b"*.foo.com", [])
            assert r[1] == ca.default_privatekey

    def test_sans(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            c1 = ca.get_cert(b"foo.com", [b"*.bar.com"])
            ca.get_cert(b"foo.bar.com", [])
            # assert c1 == c2
            c3 = ca.get_cert(b"bar.com", [])
            assert not c1 == c3

    def test_sans_change(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            ca.get_cert(b"foo.com", [b"*.bar.com"])
            cert, key, chain_file = ca.get_cert(b"foo.bar.com", [b"*.baz.com"])
            assert b"*.baz.com" in cert.altnames

    def test_expire(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            ca.STORE_CAP = 3
            ca.get_cert(b"one.com", [])
            ca.get_cert(b"two.com", [])
            ca.get_cert(b"three.com", [])

            assert (b"one.com", ()) in ca.certs
            assert (b"two.com", ()) in ca.certs
            assert (b"three.com", ()) in ca.certs

            ca.get_cert(b"one.com", [])

            assert (b"one.com", ()) in ca.certs
            assert (b"two.com", ()) in ca.certs
            assert (b"three.com", ()) in ca.certs

            ca.get_cert(b"four.com", [])

            assert (b"one.com", ()) not in ca.certs
            assert (b"two.com", ()) in ca.certs
            assert (b"three.com", ()) in ca.certs
            assert (b"four.com", ()) in ca.certs

    def test_overrides(self):
        with tutils.tmpdir() as d:
            ca1 = certutils.CertStore.from_store(os.path.join(d, "ca1"), "test")
            ca2 = certutils.CertStore.from_store(os.path.join(d, "ca2"), "test")
            assert not ca1.default_ca.get_serial_number(
            ) == ca2.default_ca.get_serial_number()

            dc = ca2.get_cert(b"foo.com", [b"sans.example.com"])
            dcp = os.path.join(d, "dc")
            f = open(dcp, "wb")
            f.write(dc[0].to_pem())
            f.close()
            ca1.add_cert_file(b"foo.com", dcp)

            ret = ca1.get_cert(b"foo.com", [])
            assert ret[0].serial == dc[0].serial


class TestDummyCert:

    def test_with_ca(self):
        with tutils.tmpdir() as d:
            ca = certutils.CertStore.from_store(d, "test")
            r = certutils.dummy_cert(
                ca.default_privatekey,
                ca.default_ca,
                b"foo.com",
                [b"one.com", b"two.com", b"*.three.com"]
            )
            assert r.cn == b"foo.com"

            r = certutils.dummy_cert(
                ca.default_privatekey,
                ca.default_ca,
                None,
                []
            )
            assert r.cn is None


class TestSSLCert:

    def test_simple(self):
        with open(tutils.test_data.path("data/text_cert"), "rb") as f:
            d = f.read()
        c1 = certutils.SSLCert.from_pem(d)
        assert c1.cn == b"google.com"
        assert len(c1.altnames) == 436

        with open(tutils.test_data.path("data/text_cert_2"), "rb") as f:
            d = f.read()
        c2 = certutils.SSLCert.from_pem(d)
        assert c2.cn == b"www.inode.co.nz"
        assert len(c2.altnames) == 2
        assert c2.digest("sha1")
        assert c2.notbefore
        assert c2.notafter
        assert c2.subject
        assert c2.keyinfo == ("RSA", 2048)
        assert c2.serial
        assert c2.issuer
        assert c2.to_pem()
        assert c2.has_expired is not None

        assert not c1 == c2
        assert c1 != c2

    def test_err_broken_sans(self):
        with open(tutils.test_data.path("data/text_cert_weird1"), "rb") as f:
            d = f.read()
        c = certutils.SSLCert.from_pem(d)
        # This breaks unless we ignore a decoding error.
        assert c.altnames is not None

    def test_der(self):
        with open(tutils.test_data.path("data/dercert"), "rb") as f:
            d = f.read()
        s = certutils.SSLCert.from_der(d)
        assert s.cn
