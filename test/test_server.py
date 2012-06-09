import urllib, urllib2, unittest
import libpathod.test, requests
import tutils

class Sanity(tutils.ProxTest):
    def test_http(self):
        assert self.pathod("205").status_code == 205
        assert self.log()


class TestHTTP(Sanity):
    pass


class TestHTTPS(Sanity):
    ssl = True


class TestProxy(tutils.ProxTest):
    def test_http(self):
        f = self.pathod("205")
        assert f.status_code == 205

        l = self.log()
        assert l[0].address
        assert "host" in l[1].headers
        assert l[2].code == 205
