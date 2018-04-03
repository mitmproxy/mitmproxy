from unittest import mock
import pytest

from mitmproxy.addons import allowremote, proxyauth
from mitmproxy.test import taddons


@pytest.mark.parametrize("allow_remote, ip, should_be_killed", [
    (True, "192.168.1.3", False),
    (True, "122.176.243.101", False),
    (False, "192.168.1.3", False),
    (False, "122.176.243.101", True),
    (True, "::ffff:1:2", False),
    (True, "fe80::", False),
    (True, "2001:4860:4860::8888", False),
    (False, "::ffff:1:2", False),
    (False, "fe80::", False),
    (False, "2001:4860:4860::8888", True),
])
@pytest.mark.asyncio
async def test_allowremote(allow_remote, ip, should_be_killed):
    ar = allowremote.AllowRemote()
    up = proxyauth.ProxyAuth()
    with taddons.context(ar, up) as tctx:
        tctx.options.allow_remote = allow_remote

        with mock.patch('mitmproxy.proxy.protocol.base.Layer') as layer:
            layer.client_conn.address = (ip, 12345)

            ar.clientconnect(layer)
            if should_be_killed:
                assert await tctx.master.await_log("Client connection was killed", "warn")
            else:
                assert tctx.master.logs == []
            tctx.master.clear()

            tctx.options.proxyauth = "any"
            ar.clientconnect(layer)
            assert tctx.master.logs == []
