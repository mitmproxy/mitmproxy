import urwid

import mitmproxy.tools.console.flowlist as flowlist
from mitmproxy.tools import console
from mitmproxy import proxy
from mitmproxy import options


class TestFlowlist:
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 1
        o = options.Options(**opts)
        return console.master.ConsoleMaster(o, proxy.DummyServer())

    def test_logbuffer_set_focus(self):
        m = self.mkmaster()
        b = flowlist.LogBufferBox(m)
        e = urwid.Text("Log message")
        m.logbuffer.append(e)
        m.logbuffer.append(e)

        assert len(m.logbuffer) == 2
        b.set_focus(0)
        assert m.logbuffer.focus == 0
        b.set_focus(1)
        assert m.logbuffer.focus == 1
        b.set_focus(2)
        assert m.logbuffer.focus == 1
