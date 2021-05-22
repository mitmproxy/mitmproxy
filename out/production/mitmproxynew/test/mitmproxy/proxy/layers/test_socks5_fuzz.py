from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy import options
from mitmproxy.connection import Client
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers.modes import Socks5Proxy

opts = options.Options()
tctx = Context(Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)


@given(binary())
def test_socks5_fuzz(data):
    layer = Socks5Proxy(tctx)
    list(layer.handle_event(DataReceived(tctx.client, data)))
