import tservers
from netlib.certutils import SSLCert

class TestTcp(tservers.IgnoreProxTest):
    ignore = []

    def test_simple(self):
        # i = ignore (tcp passthrough), n = normal
        pi, pn = self.pathocs()
        i = pi.request("get:'/p/304'")
        i2 = pi.request("get:'/p/304'")
        n = pn.request("get:'/p/304'")

        assert i.status_code == i2.status_code == n.status_code == 304

        i_cert = SSLCert(i.sslinfo.certchain[0])
        i2_cert = SSLCert(i2.sslinfo.certchain[0])
        n_cert = SSLCert(n.sslinfo.certchain[0])

        assert i_cert == i2_cert
        assert not i_cert == n_cert