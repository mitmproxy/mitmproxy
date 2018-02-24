import urwid

from mitmproxy import options
from mitmproxy.tools import console
from ... import tservers


class TestMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        if "verbosity" not in opts:
            opts["verbosity"] = 'warn'
        o = options.Options(**opts)
        m = console.master.ConsoleMaster(o)
        m.addons.trigger("configure", o.keys())
        return m

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            try:
                self.dummy_cycle(m, 1, b"")
            except urwid.ExitMainLoop:
                pass
            assert len(m.view) == i
