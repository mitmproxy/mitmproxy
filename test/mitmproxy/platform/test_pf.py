import sys
import pytest
from mitmproxy.platform import pf


class TestLookup:

    def test_simple(self, tdata):
        if sys.platform == "freebsd10":
            p = tdata.path("mitmproxy/data/pf02")
        else:
            p = tdata.path("mitmproxy/data/pf01")
        with open(p, "rb") as f:
            d = f.read()

        assert pf.lookup("192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        assert pf.lookup("::ffff:192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("192.168.1.112", 40000, d)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("192.168.1.111", 40001, d)
