import pytest
from unittest import mock

from mitmproxy.addons import check_ca
from mitmproxy.test import taddons


class TestCheckCA:

    @pytest.mark.parametrize('expired', [False, True])
    @pytest.mark.asyncio
    async def test_check_ca(self, expired):
        msg = 'The mitmproxy certificate authority has expired!'

        a = check_ca.CheckCA()
        with taddons.context(a) as tctx:
            tctx.master.server = mock.MagicMock()
            tctx.master.server.config.certstore.default_ca.has_expired = mock.MagicMock(
                return_value = expired
            )
            tctx.configure(a)
            assert await tctx.master.await_log(msg) == expired
