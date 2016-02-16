from . import tutils, tservers


class TestApp(tservers.HTTPProxyTest):

    def test_basic(self):
        assert self.app("/").status_code == 200

    def test_cert(self):
        with tutils.tmpdir() as d:
            for ext in ["pem", "p12"]:
                resp = self.app("/cert/%s" % ext)
                assert resp.status_code == 200
                assert resp.content
