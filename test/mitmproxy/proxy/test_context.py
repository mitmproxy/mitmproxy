from mitmproxy.proxy import context
from mitmproxy.test import tflow, taddons


def test_context():
    with taddons.context() as tctx:
        c = context.Context(
            tflow.tclient_conn(),
            tctx.options
        )
        assert repr(c)
        c.layers.append(1)
        assert repr(c)
        c2 = c.fork()
        c.layers.append(2)
        c2.layers.append(3)
        assert c.layers == [1, 2]
        assert c2.layers == [1, 3]
