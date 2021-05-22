import pytest

from mitmproxy import connection
from mitmproxy.addons import block
from mitmproxy.test import taddons


@pytest.mark.parametrize("block_global, block_private, should_be_killed, address", [
    # block_global: loopback
    (True, False, False, ("127.0.0.1",)),
    (True, False, False, ("::1",)),
    # block_global: private
    (True, False, False, ("10.0.0.1",)),
    (True, False, False, ("172.20.0.1",)),
    (True, False, False, ("192.168.1.1",)),
    (True, False, False, ("::ffff:10.0.0.1",)),
    (True, False, False, ("::ffff:172.20.0.1",)),
    (True, False, False, ("::ffff:192.168.1.1",)),
    (True, False, False, ("fe80::",)),
    (True, False, False, (r"::ffff:192.168.1.1%scope",)),
    # block_global: global
    (True, False, True, ("1.1.1.1",)),
    (True, False, True, ("8.8.8.8",)),
    (True, False, True, ("216.58.207.174",)),
    (True, False, True, ("::ffff:1.1.1.1",)),
    (True, False, True, ("::ffff:8.8.8.8",)),
    (True, False, True, ("::ffff:216.58.207.174",)),
    (True, False, True, ("2001:4860:4860::8888",)),
    (True, False, True, (r"2001:4860:4860::8888%scope",)),

    # block_private: loopback
    (False, True, False, ("127.0.0.1",)),
    (False, True, False, ("::1",)),
    # block_private: private
    (False, True, True, ("10.0.0.1",)),
    (False, True, True, ("172.20.0.1",)),
    (False, True, True, ("192.168.1.1",)),
    (False, True, True, ("::ffff:10.0.0.1",)),
    (False, True, True, ("::ffff:172.20.0.1",)),
    (False, True, True, ("::ffff:192.168.1.1",)),
    (False, True, True, (r"::ffff:192.168.1.1%scope",)),
    (False, True, True, ("fe80::",)),
    # block_private: global
    (False, True, False, ("1.1.1.1",)),
    (False, True, False, ("8.8.8.8",)),
    (False, True, False, ("216.58.207.174",)),
    (False, True, False, ("::ffff:1.1.1.1",)),
    (False, True, False, ("::ffff:8.8.8.8",)),
    (False, True, False, ("::ffff:216.58.207.174",)),
    (False, True, False, (r"::ffff:216.58.207.174%scope",)),
    (False, True, False, ("2001:4860:4860::8888",)),
])
@pytest.mark.asyncio
async def test_block_global(block_global, block_private, should_be_killed, address):
    ar = block.Block()
    with taddons.context(ar) as tctx:
        tctx.configure(ar, block_global=block_global, block_private=block_private)
        client = connection.Client(address, ("127.0.0.1", 8080), 1607699500)
        ar.client_connected(client)
        assert bool(client.error) == should_be_killed
