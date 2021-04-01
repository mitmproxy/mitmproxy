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
        assert pf.lookup("2a01:e35:8bae:50f0:396f:e6c7:f4f1:f3db", 40002, d) == ("2a03:2880:f21f:c5:face:b00c::167", 443)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("2a01:e35:8bae:50f0:396f:e6c7:f4f1:f3db", 40003, d)
        with pytest.raises(Exception, match="Could not resolve original destination"):
            pf.lookup("2a01:e35:face:face:face:face:face:face", 40003, d)
