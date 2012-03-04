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


class uparse_text_cert(libpry.AutoTree):
    def test_simple(self):
        c = certutils.SSLCert(file("data/text_cert", "r").read())
        assert c.cn == "google.com"
        assert len(c.altnames) == 436

        c = certutils.SSLCert(file("data/text_cert_2", "r").read())
        assert c.cn == "www.inode.co.nz"
        assert len(c.altnames) == 2


tests = [
    uparse_text_cert(),
    udummy_ca(),
    udummy_cert(),
]
