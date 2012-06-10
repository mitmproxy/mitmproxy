import urllib, urllib2, unittest
import time
import libpathod.test, requests
import tutils

"""
    Note that the choice of response code in these tests matters more than you
    might think. libcurl treats a 304 response code differently from, say, a
    200 response code - it will correctly terminate a 304 response with no
    content-length header, whereas it will block forever waiting for content
    for a 200 response.
"""

class Sanity(tutils.ProxTest):
    def test_http(self):
        assert self.pathod("304").status_code == 304
        assert self.log()


class TestHTTP(Sanity):
    pass


class TestHTTPS(Sanity):
    ssl = True


class TestReverse(Sanity):
    reverse = True


class TestProxy(tutils.ProxTest):
    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.log()
        assert l[0].address
        assert "host" in l[1].headers
        assert l[2].code == 304
