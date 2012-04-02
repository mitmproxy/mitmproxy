import os
import libpry
from libmproxy import certutils


class udummy_ca(libpry.AutoTree):
    def test_all(self):
        d = self.tmpdir()
        path = os.path.join(d, "foo/cert.cnf")
        assert certutils.dummy_ca(path)
        assert os.path.exists(path)

        path = os.path.join(d, "foo/cert2.pem")
        assert certutils.dummy_ca(path)
        assert os.path.exists(path)
        assert os.path.exists(os.path.join(d, "foo/cert2-cert.pem"))
        assert os.path.exists(os.path.join(d, "foo/cert2-cert.p12"))


class udummy_cert(libpry.AutoTree):
    def test_with_ca(self):
        d = self.tmpdir()
        cacert = os.path.join(d, "foo/cert.cnf")
        assert certutils.dummy_ca(cacert)
        p = certutils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com",
            ["one.com", "two.com", "*.three.com"]
        )
        assert os.path.exists(p)

        # Short-circuit
        assert certutils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com",
            []
        )

    def test_no_ca(self):
        d = self.tmpdir()
        p = certutils.dummy_cert(
            d,
            None,
            "foo.com",
            []
        )
        assert os.path.exists(p)


class uSSLCert(libpry.AutoTree):
    def test_simple(self):
        c = certutils.SSLCert(file("data/text_cert", "r").read())
        assert c.cn == "google.com"
        assert len(c.altnames) == 436

        c = certutils.SSLCert(file("data/text_cert_2", "r").read())
        assert c.cn == "www.inode.co.nz"
        assert len(c.altnames) == 2
        assert c.digest("sha1")
        assert c.notbefore
        assert c.notafter
        assert c.subject
        assert c.keyinfo == ("RSA", 2048)
        assert c.serial
        assert c.issuer
        c.has_expired

    def test_der(self):
        d = file("data/dercert").read()
        s = certutils.SSLCert.from_der(d)
        assert s.cn


tests = [
    udummy_ca(),
    udummy_cert(),
    uSSLCert(),
]
