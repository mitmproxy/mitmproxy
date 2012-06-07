import urllib, urllib2
import libpathod.test, requests
import libpry
import tutils

class uSanity(tutils.ProxTest):
    def test_http(self):
        assert self.pathod("205").status_code == 205
        assert self.log()


class uProxy(tutils.ProxTest):
    def test_http(self):
        f = self._get()
        assert f.code == 200
        assert f.read()
        f.close()

        l = self.log()
        assert l[0].address
        assert "host" in l[1].headers
        assert l[2].code == 200


tests = [
    tutils.TestServer(), [
        uSanity(),
    ],
    tutils.TestServer(ssl=True), [
        uSanity(),
    ],
]
