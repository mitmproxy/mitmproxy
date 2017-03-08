from mitmproxy import exceptions
from mitmproxy.addons import core_option_validation
from mitmproxy.test import taddons
import pytest
from unittest import mock


def test_simple():
    sa = core_option_validation.CoreOptionValidation()
    with taddons.context() as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, body_size_limit = "invalid")
        tctx.configure(sa, body_size_limit = "1m")
        assert tctx.options._processed["body_size_limit"]

        with pytest.raises(exceptions.OptionsError, match="mutually exclusive"):
            tctx.configure(
                sa,
                add_upstream_certs_to_client_chain = True,
                upstream_cert = False
            )
        with pytest.raises(exceptions.OptionsError, match="Invalid mode"):
            tctx.configure(
                sa,
                mode = "Flibble"
            )


@mock.patch("mitmproxy.platform.original_addr", None)
def test_no_transparent():
    sa = core_option_validation.CoreOptionValidation()
    with taddons.context() as tctx:
        with pytest.raises(Exception, match="Transparent mode not supported"):
            tctx.configure(sa, mode = "transparent")


@mock.patch("mitmproxy.platform.original_addr")
def test_modes(m):
    sa = core_option_validation.CoreOptionValidation()
    with taddons.context() as tctx:
        tctx.configure(sa, mode = "reverse:http://localhost")
        with pytest.raises(Exception, match="Invalid server specification"):
            tctx.configure(sa, mode = "reverse:")
