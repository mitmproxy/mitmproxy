import pytest

from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.test import tutils


class TestProxyConfig:
    def test_invalid_cadir(self):
        opts = options.Options()
        opts.cadir = "foo"
        with pytest.raises(exceptions.OptionsError, match="parent directory does not exist"):
            ProxyConfig(opts)

    def test_invalid_certificate(self):
        opts = options.Options()
        opts.certs = [tutils.test_data.path("mitmproxy/data/dumpfile-011")]
        with pytest.raises(exceptions.OptionsError, match="Invalid certificate format"):
            ProxyConfig(opts)
