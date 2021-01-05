import urwid

import pytest

from mitmproxy import options, hooks
from mitmproxy.tools import console

from ... import tservers


@pytest.mark.asyncio
class TestMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        o = options.Options(**opts)
        m = console.master.ConsoleMaster(o)
        m.addons.trigger(hooks.ConfigureHook(o.keys()))
        return m

    async def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            try:
                await self.dummy_cycle(m, 1, b"")
            except urwid.ExitMainLoop:
                pass
            assert len(m.view) == i
