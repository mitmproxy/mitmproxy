import cStringIO, textwrap
from cStringIO import StringIO
import libpry
from libmproxy import proxy, flow
import tutils


class TestProxyError:
    def test_simple(self):
        p = proxy.ProxyError(111, "msg")
        assert repr(p)

