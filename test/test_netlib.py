import cStringIO
from libmproxy import netlib


class TestFileLike:
    def test_wrap(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = netlib.FileLike(s)
        s.flush()
        assert s.readline() == "foobar\n"
        assert s.readline() == "foobar"
        # Test __getattr__
        assert s.isatty


