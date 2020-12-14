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
        opts.certs = [tdata.path("mitmproxy/data/dumpfile-011.bin")]
        with pytest.raises(exceptions.OptionsError, match="Invalid certificate format"):
            ProxyConfig(opts)

    def test_cannot_set_both_allow_and_filter_options(self):
        opts = options.Options()
        opts.ignore_hosts = ["foo"]
        opts.allow_hosts = ["bar"]
        with pytest.raises(exceptions.OptionsError, match="--ignore-hosts and --allow-hosts are "
                                                          "mutually exclusive; please choose "
                                                          "one."):
            ProxyConfig(opts)
