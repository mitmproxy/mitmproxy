from libmproxy import encoding
import libpry

import cStringIO

class uidentity(libpry.AutoTree):
    def test_simple(self):
        assert "string" == encoding.decode("identity", "string")
        assert "string" == encoding.encode("identity", "string")

    def test_fallthrough(self):
        assert None == encoding.decode("nonexistent encoding", "string")

class ugzip(libpry.AutoTree):
    def test_simple(self):
        assert "string" == encoding.decode("gzip", encoding.encode("gzip", "string"))
        assert None == encoding.decode("gzip", "bogus")

class udeflate(libpry.AutoTree):
    def test_simple(self):
        assert "string" == encoding.decode("deflate", encoding.encode("deflate", "string"))
        assert "string" == encoding.decode("deflate", encoding.encode("deflate", "string")[2:-4])
        assert None == encoding.decode("deflate", "bogus")

tests = [
    uidentity(),
    ugzip(),
    udeflate()
]
