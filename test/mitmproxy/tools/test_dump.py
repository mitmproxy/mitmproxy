import pytest

from mitmproxy import options
from mitmproxy.tools import dump


class TestDumpMaster:
    @pytest.mark.parametrize("termlog", [False, True])
    async def test_addons_termlog(self, capsys, termlog):
        o = options.Options()
        m = dump.DumpMaster(o, with_termlog=termlog)
        assert (m.addons.get("termlog") is not None) == termlog
        await m.done()

    @pytest.mark.parametrize("dumper", [False, True])
    async def test_addons_dumper(self, capsys, dumper):
        o = options.Options()
        m = dump.DumpMaster(o, with_dumper=dumper, with_termlog=False)
        assert (m.addons.get("dumper") is not None) == dumper
        await m.done()
