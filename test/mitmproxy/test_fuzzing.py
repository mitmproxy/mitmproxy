from . import tservers

"""
    A collection of errors turned up by fuzzing. Errors are integrated here
    after being fixed to check for regressions.
"""


class TestFuzzy(tservers.HTTPProxyTest):

    def test_idna_err(self):
        req = r'get:"http://localhost:%s":i10,"\xc6"'
        p = self.pathoc()
        with p.connect():
            assert p.request(req % self.server.port).status_code == 400

    def test_nullbytes(self):
        req = r'get:"http://localhost:%s":i19,"\x00"'
        p = self.pathoc()
        with p.connect():
            assert p.request(req % self.server.port).status_code == 400

    def test_invalid_ipv6_url(self):
        req = 'get:"http://localhost:%s":i13,"["'
        p = self.pathoc()
        with p.connect():
            resp = p.request(req % self.server.port)
        assert resp.status_code == 400

    # def test_invalid_upstream(self):
    #     req = r"get:'http://localhost:%s/p/200:i10,\x27+\x27'"
    #     p = self.pathoc()
    #     assert p.request(req % self.server.port).status_code == 502

    # def test_upstream_disconnect(self):
    #     req = r'200:d0'
    #     p = self.pathod(req)
    #     assert p.status_code == 502
