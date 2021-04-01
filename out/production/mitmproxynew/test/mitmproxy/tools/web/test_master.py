import pytest

from mitmproxy import options
from mitmproxy.tools.web import master

from ... import tservers


class TestWebMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        o = options.Options(**opts)
        return master.WebMaster(o)

    @pytest.mark.asyncio
    async def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            await self.dummy_cycle(m, 1, b"")
            assert len(m.view) == i
