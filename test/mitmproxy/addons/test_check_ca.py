import pytest
from unittest import mock

from mitmproxy.addons import check_ca
from mitmproxy.test import taddons


class TestCheckCA:

    @pytest.mark.parametrize('expired', [False, True])
    def test_check_ca(self, expired):
        msg = 'The mitmproxy certificate authority has expired!'

        with taddons.context() as tctx:
            tctx.master.server = mock.MagicMock()
            tctx.master.server.config.certstore.default_ca.has_expired = mock.MagicMock(return_value=expired)
            a = check_ca.CheckCA()
            tctx.configure(a)
            assert any(msg in m for l, m in tctx.master.logs) is expired
