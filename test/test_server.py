import urllib, urllib2
from libmproxy import flow
import tutils

class uSanity(tutils.ProxTest):
    def test_http(self):
        """
            Just check that the HTTP server is running.
        """
        f = urllib.urlopen("http://127.0.0.1:%s"%tutils.HTTP_PORT)
        assert f.read()

    def test_https(self):
        """
            Just check that the HTTPS server is running.
        """
        f = urllib.urlopen("https://127.0.0.1:%s"%tutils.HTTPS_PORT)
        assert f.read()


class uProxy(tutils.ProxTest):
    HOST = "127.0.0.1"
    def _get(self, host=HOST):
        r = urllib2.Request("http://%s:%s"%(host, tutils.HTTP_PORT))
        r.set_proxy("127.0.0.1:%s"%tutils.PROXL_PORT, "http")
        return urllib2.urlopen(r)

    def _sget(self, host=HOST):
        proxy_support = urllib2.ProxyHandler(
                            {"https" : "https://127.0.0.1:%s"%tutils.PROXL_PORT}
                        )
        opener = urllib2.build_opener(proxy_support)
        r = urllib2.Request("https://%s:%s"%(host, tutils.HTTPS_PORT))
        return opener.open(r)

    def test_http(self):
        f = self._get()
        assert f.code == 200
        assert f.read()
        f.close()
            
        l = self.log()
        assert l[0].address
        assert l[1].headers.has_key("host")
        assert l[2].code == 200

    def test_https(self):
        f = self._sget()
        assert f.code == 200
        assert f.read()
        f.close()

        l = self.log()
        assert l[0].address
        assert l[1].headers.has_key("host")
        assert l[2].code == 200

    # Disable these two for now: they take a long time.
    def _test_http_nonexistent(self):
        f = self._get("nonexistent")
        assert f.code == 200
        assert "Error" in f.read()

    def _test_https_nonexistent(self):
        f = self._sget("nonexistent")
        assert f.code == 200
        assert "Error" in f.read()


tests = [
    tutils.TestServers(), [
        uSanity(),
        uProxy(),
    ]
]
