from mitmproxy.addons import termstatus
from mitmproxy.test import taddons


def test_configure():
    ts = termstatus.TermStatus()
    with taddons.context() as ctx:
        ts.running()
        assert not ctx.master.event_log
        ctx.configure(ts, server=True)
        ts.running()
        assert ctx.master.event_log
