import sys
from mitmproxy.platform import pf
from . import tutils


class TestLookup:

    def test_simple(self):
        if sys.platform == "freebsd10":
            p = tutils.test_data.path("data/pf02")
            d = open(p, "rb").read()
        else:
            p = tutils.test_data.path("data/pf01")
            d = open(p, "rb").read()
        assert pf.lookup("192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        tutils.raises(
            "Could not resolve original destination",
            pf.lookup,
            "192.168.1.112",
            40000,
            d)
        tutils.raises(
            "Could not resolve original destination",
            pf.lookup,
            "192.168.1.111",
            40001,
            d)
