import sys
import pytest
from mitmproxy.platform import pf
from mitmproxy.test import tutils


class TestLookup:

    def test_simple(self):
        if sys.platform == "freebsd10":
            p = tutils.test_data.path("mitmproxy/data/pf02")
        else:
            p = tutils.test_data.path("mitmproxy/data/pf01")
        with open(p, "rb") as f:
            d = f.read()

        assert pf.lookup("192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("192.168.1.112", 40000, d)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("192.168.1.111", 40001, d)
