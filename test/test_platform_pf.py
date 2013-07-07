import tutils
from libmproxy.platform import pf


class TestLookup:
    def test_simple(self):
        p = tutils.test_data.path("data/pf01")
        d = open(p,"rb").read()
        assert pf.lookup("192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        assert not pf.lookup("192.168.1.112", 40000, d)
        assert not pf.lookup("192.168.1.111", 40001, d)


