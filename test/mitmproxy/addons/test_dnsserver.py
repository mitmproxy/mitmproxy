import pytest

from mitmproxy import exceptions
from mitmproxy.addons.dnsserver import DnsServer
from mitmproxy.proxy.layers.dns import DnsMode
from mitmproxy.test import taddons


def test_options():
    ds = DnsServer()
    with taddons.context(ds) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ds, dns_mode="invalid")
        tctx.configure(ds, dns_mode="simple")
        assert ds.mode is DnsMode.Simple

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ds, dns_mode="forward")
        tctx.configure(ds, dns_mode="forward:8.8.8.8")
        assert ds.mode is DnsMode.Forward
        assert ds.forward_addr == ("8.8.8.8", 53)

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ds, dns_mode="forward:8.8.8.8:invalid")
        tctx.configure(ds, dns_mode="forward:8.8.8.8:53")
        assert ds.mode is DnsMode.Forward
        assert ds.forward_addr == ("8.8.8.8", 53)
