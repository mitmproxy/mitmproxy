from unittest import mock

import pytest

from mitmproxy import options
from mitmproxy.tools import dump


class TestDumpMaster:
    def mkmaster(self, **opts):
        o = options.Options(**opts)
        m = dump.DumpMaster(o, with_termlog=False, with_dumper=False)
        return m

    @pytest.mark.parametrize("termlog", [False, True])
    async def test_addons_termlog(self, termlog):
        with mock.patch("sys.stdout"):
            o = options.Options()
            m = dump.DumpMaster(o, with_termlog=termlog)
            assert (m.addons.get("termlog") is not None) == termlog

    @pytest.mark.parametrize("dumper", [False, True])
    async def test_addons_dumper(self, dumper):
        with mock.patch("sys.stdout"):
            o = options.Options()
            m = dump.DumpMaster(o, with_dumper=dumper)
            assert (m.addons.get("dumper") is not None) == dumper
