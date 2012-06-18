import cStringIO, textwrap
from cStringIO import StringIO
import libpry
from libmproxy import proxy, flow
import tutils


class TestProxyError:
    def test_simple(self):
        p = proxy.ProxyError(111, "msg")
        assert repr(p)


class TestAppRegistry:
    def test_add_get(self):
        ar = proxy.AppRegistry()
        ar.add("foo", "domain", 80)

        r = tutils.treq()
        r.host = "domain"
        r.port = 80
        assert ar.get(r)

        r.port = 81
        assert not ar.get(r)
