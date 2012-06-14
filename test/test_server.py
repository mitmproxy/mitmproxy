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

class SanityMixin:
    def test_http(self):
        assert self.pathod("304").status_code == 304
        assert self.log()

    def test_large(self):
        assert len(self.pathod("200:b@50k").content) == 1024*50


class TestHTTP(tutils.HTTPProxTest, SanityMixin):
    pass


class TestHTTPS(tutils.HTTPProxTest, SanityMixin):
    ssl = True


class TestReverse(tutils.ReverseProxTest, SanityMixin):
    reverse = True


class TestTransparent(tutils.TransparentProxTest, SanityMixin):
    transparent = True


class TestProxy(tutils.HTTPProxTest):
    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.log()
        assert l[0].address
        assert "host" in l[1].headers
        assert l[2].code == 304
