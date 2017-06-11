import pytest

from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.test import tutils


class TestProxyConfig:
    def test_upstream_cert_insecure(self):
        opts = options.Options()
        opts.add_upstream_certs_to_client_chain = True
        with pytest.raises(exceptions.OptionsError, match="verify-upstream-cert"):
            ProxyConfig(opts)

    def test_invalid_cadir(self):
        opts = options.Options()
        opts.cadir = "foo"
        with pytest.raises(exceptions.OptionsError, match="parent directory does not exist"):
            ProxyConfig(opts)

    def test_invalid_client_certs(self):
        opts = options.Options()
        opts.client_certs = "foo"
        with pytest.raises(exceptions.OptionsError, match="certificate path does not exist"):
            ProxyConfig(opts)

    def test_valid_client_certs(self):
        opts = options.Options()
        opts.client_certs = tutils.test_data.path("mitmproxy/data/clientcert/")
        p = ProxyConfig(opts)
        assert p.client_certs

    def test_invalid_certificate(self):
        opts = options.Options()
        opts.certs = [tutils.test_data.path("mitmproxy/data/dumpfile-011")]
        with pytest.raises(exceptions.OptionsError, match="Invalid certificate format"):
            ProxyConfig(opts)
