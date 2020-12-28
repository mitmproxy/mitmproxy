import argparse

import pytest

from mitmproxy import options
from mitmproxy.tools import cmdline
from mitmproxy.tools import main


class MockParser(argparse.ArgumentParser):
    """
    argparse.ArgumentParser sys.exits() by default.
    Make it more testable by throwing an exception instead.
    """

    def error(self, message):
        raise Exception(message)


class TestProcessProxyOptions:

    def p(self, *args):
        parser = MockParser()
        opts = options.Options()
        cmdline.common_options(parser, opts)
        args = parser.parse_args(args=args)
        pconf = main.process_options(parser, opts, args)
        return parser, pconf

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_certs(self, tdata):
        with pytest.raises(Exception, match="ambiguous option"):
            self.assert_noerr(
                "--cert",
                tdata.path("mitmproxy/data/testkey.pem"))
