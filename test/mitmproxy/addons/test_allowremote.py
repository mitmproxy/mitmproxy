from unittest import mock
import pytest

from mitmproxy.addons import allowremote, proxyauth
from mitmproxy.test import taddons


@pytest.mark.parametrize("allow_remote, should_be_killed, address", [
    (True, False, ("10.0.0.1",)),
    (True, False, ("172.20.0.1",)),
    (True, False, ("192.168.1.1",)),
    (True, False, ("1.1.1.1",)),
    (True, False, ("8.8.8.8",)),
    (True, False, ("216.58.207.174",)),
    (True, False, ("::ffff:1.1.1.1",)),
    (True, False, ("::ffff:8.8.8.8",)),
    (True, False, ("::ffff:216.58.207.174",)),
    (True, False, ("::ffff:10.0.0.1",)),
    (True, False, ("::ffff:172.20.0.1",)),
    (True, False, ("::ffff:192.168.1.1",)),
    (True, False, ("fe80::",)),
    (True, False, ("2001:4860:4860::8888",)),
    (False, False, ("10.0.0.1",)),
    (False, False, ("172.20.0.1",)),
    (False, False, ("192.168.1.1",)),
    (False, True, ("1.1.1.1",)),
    (False, True, ("8.8.8.8",)),
    (False, True, ("216.58.207.174",)),
    (False, True, ("::ffff:1.1.1.1",)),
    (False, True, ("::ffff:8.8.8.8",)),
    (False, True, ("::ffff:216.58.207.174",)),
    (False, False, ("::ffff:10.0.0.1",)),
    (False, False, ("::ffff:172.20.0.1",)),
    (False, False, ("::ffff:192.168.1.1",)),
    (False, False, ("fe80::",)),
    (False, True, ("2001:4860:4860::8888",)),
])
@pytest.mark.asyncio
async def test_allowremote(allow_remote, should_be_killed, address):
    if allow_remote:
        # prevent faulty tests
        assert not should_be_killed

    ar = allowremote.AllowRemote()
    up = proxyauth.ProxyAuth()
    with taddons.context(ar, up) as tctx:
        tctx.options.allow_remote = allow_remote

        with mock.patch('mitmproxy.proxy.protocol.base.Layer') as layer:
            layer.client_conn.address = address

            ar.clientconnect(layer)
            if should_be_killed:
                assert await tctx.master.await_log("Client connection was killed", "warn")
            else:
                assert tctx.master.logs == []
            tctx.master.clear()

            tctx.options.proxyauth = "any"
            ar.clientconnect(layer)
            assert tctx.master.logs == []
