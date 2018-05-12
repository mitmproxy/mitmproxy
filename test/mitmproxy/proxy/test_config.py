import pytest

from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.proxy.config import ProxyConfig


class TestProxyConfig:
    def test_invalid_confdir(self):
        opts = options.Options()
        opts.confdir = "foo"
        with pytest.raises(exceptions.OptionsError, match="parent directory does not exist"):
            ProxyConfig(opts)

    def test_invalid_certificate(self, tdata):
        opts = options.Options()
        opts.certs = [tdata.path("mitmproxy/data/dumpfile-011")]
        with pytest.raises(exceptions.OptionsError, match="Invalid certificate format"):
            ProxyConfig(opts)
