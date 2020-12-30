import os
from pathlib import Path

import pytest

from mitmproxy import certs
from ..conftest import skip_windows


# class TestDNTree:
#     def test_simple(self):
#         d = certs.DNTree()
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
#         d = certs.DNTree()
#         d.add("foo.com", "foo")
#         assert not d.get("*.foo.com")
#         d.add("*.foo.com", "wild")
#
#         d = certs.DNTree()
#         d.add("*", "foo")
#         assert d.get("foo.com") == "foo"
#         assert d.get("*.foo.com") == "foo"
#         assert d.get("com") == "foo"


@pytest.fixture()
def tstore(tdata):
    return certs.CertStore.from_store(tdata.path("mitmproxy/data/confdir"), "mitmproxy", 2048)


class TestCertStore:

    def test_create_explicit(self, tmpdir):
        ca = certs.CertStore.from_store(str(tmpdir), "test", 2048)
        assert ca.get_cert(b"foo", [])

        ca2 = certs.CertStore.from_store(str(tmpdir), "test", 2048)
        assert ca2.get_cert(b"foo", [])

        assert ca.default_ca.serial == ca2.default_ca.serial

    def test_create_no_common_name(self, tstore):
        assert tstore.get_cert(None, []).cert.cn is None

    def test_sans(self, tstore):
        c1 = tstore.get_cert(b"foo.com", [b"*.bar.com"])
        tstore.get_cert(b"foo.bar.com", [])
        # assert c1 == c2
        c3 = tstore.get_cert(b"bar.com", [])
        assert not c1 == c3

    def test_sans_change(self, tstore):
        tstore.get_cert(b"foo.com", [b"*.bar.com"])
        entry = tstore.get_cert(b"foo.bar.com", [b"*.baz.com"])
        assert b"*.baz.com" in entry.cert.altnames

    def test_expire(self, tstore):
        tstore.STORE_CAP = 3
        tstore.get_cert(b"one.com", [])
        tstore.get_cert(b"two.com", [])
        tstore.get_cert(b"three.com", [])

        assert (b"one.com", ()) in tstore.certs
        assert (b"two.com", ()) in tstore.certs
        assert (b"three.com", ()) in tstore.certs

        tstore.get_cert(b"one.com", [])

        assert (b"one.com", ()) in tstore.certs
        assert (b"two.com", ()) in tstore.certs
        assert (b"three.com", ()) in tstore.certs

        tstore.get_cert(b"four.com", [])

        assert (b"one.com", ()) not in tstore.certs
        assert (b"two.com", ()) in tstore.certs
        assert (b"three.com", ()) in tstore.certs
        assert (b"four.com", ()) in tstore.certs

    def test_overrides(self, tmp_path):
        ca1 = certs.CertStore.from_store(tmp_path / "ca1", "test", 2048)
        ca2 = certs.CertStore.from_store(tmp_path / "ca2", "test", 2048)
        assert not ca1.default_ca.serial == ca2.default_ca.serial

        dc = ca2.get_cert(b"foo.com", [b"sans.example.com"])
        dcp = tmp_path / "dc"
        dcp.write_bytes(dc.cert.to_pem())
        ca1.add_cert_file("foo.com", dcp)

        ret = ca1.get_cert(b"foo.com", [])
        assert ret.cert.serial == dc.cert.serial

    def test_create_dhparams(self, tmp_path):
        filename = tmp_path / "dhparam.pem"
        certs.CertStore.load_dhparam(filename)
        assert filename.exists()

    @skip_windows
    def test_umask_secret(self, tmpdir):
        filename = str(tmpdir.join("secret"))
        with certs.CertStore.umask_secret(), open(filename, "wb"):
            pass
        # TODO: How do we actually attempt to read that file as another user?
        assert os.stat(filename).st_mode & 0o77 == 0


class TestDummyCert:

    def test_with_ca(self, tstore):
        r = certs.dummy_cert(
            tstore.default_privatekey,
            tstore.default_ca._cert,
            b"foo.com",
            [b"one.com", b"two.com", b"*.three.com", b"127.0.0.1"],
            b"Foo Ltd."
        )
        assert r.cn == b"foo.com"
        assert r.altnames == [b"one.com", b"two.com", b"*.three.com", b"127.0.0.1"]
        assert r.organization == b"Foo Ltd."

        r = certs.dummy_cert(
            tstore.default_privatekey,
            tstore.default_ca._cert,
            None,
            [],
            None
        )
        assert r.cn is None
        assert r.organization is None
        assert r.altnames == []


class TestCert:

    def test_simple(self, tdata):
        with open(tdata.path("mitmproxy/net/data/text_cert"), "rb") as f:
            d = f.read()
        c1 = certs.Cert.from_pem(d)
        assert c1.cn == b"google.com"
        assert len(c1.altnames) == 436
        assert c1.organization == b"Google Inc"

        with open(tdata.path("mitmproxy/net/data/text_cert_2"), "rb") as f:
            d = f.read()
        c2 = certs.Cert.from_pem(d)
        assert c2.cn == b"www.inode.co.nz"
        assert len(c2.altnames) == 2
        assert c2.fingerprint()
        assert c2.notbefore
        assert c2.notafter
        assert c2.subject
        assert c2.keyinfo == ("RSA", 2048)
        assert c2.serial
        assert c2.issuer
        assert c2.to_pem()
        assert c2.has_expired is not None

        assert c1 != c2

    def test_err_broken_sans(self, tdata):
        with open(tdata.path("mitmproxy/net/data/text_cert_weird1"), "rb") as f:
            d = f.read()
        c = certs.Cert.from_pem(d)
        # This breaks unless we ignore a decoding error.
        assert c.altnames is not None

    def test_state(self, tdata):
        with open(tdata.path("mitmproxy/net/data/text_cert"), "rb") as f:
            d = f.read()
        c = certs.Cert.from_pem(d)

        c.get_state()
        c2 = c.copy()
        a = c.get_state()
        b = c2.get_state()
        assert a == b
        assert c == c2
        assert c is not c2

        c2.set_state(a)
        assert c == c2

    def test_from_store_with_passphrase(self, tdata, tstore):
        tstore.add_cert_file("*", Path(tdata.path("mitmproxy/data/mitmproxy.pem")), b"password")

        assert tstore.get_cert(b"foo", [])
