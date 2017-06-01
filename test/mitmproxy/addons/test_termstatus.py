from mitmproxy.addons import termstatus
from mitmproxy.test import taddons


def test_configure():
    ts = termstatus.TermStatus()
    with taddons.context() as ctx:
        ctx.configure(ts, server=False)
        ts.running()
        assert not ctx.master.logs
        ctx.configure(ts, server=True)
        ts.running()
        assert ctx.master.logs
