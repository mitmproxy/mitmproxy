import asyncio
import pytest

from mitmproxy.addons import keepserving
from mitmproxy.test import taddons
from mitmproxy import command


class Dummy:
    def __init__(self, val: bool):
        self.val = val

    def load(self, loader):
        loader.add_option("client_replay", bool, self.val, "test")
        loader.add_option("server_replay", bool, self.val, "test")
        loader.add_option("rfile", bool, self.val, "test")

    @command.command("readfile.reading")
    def readfile(self) -> bool:
        return self.val

    @command.command("replay.client.count")
    def creplay(self) -> int:
        return 1 if self.val else 0

    @command.command("replay.server.count")
    def sreplay(self) -> int:
        return 1 if self.val else 0


class TKS(keepserving.KeepServing):
    _is_shutdown = False

    def shutdown(self):
        self.is_shutdown = True


@pytest.mark.asyncio
async def test_keepserving():
    ks = TKS()
    d = Dummy(True)
    with taddons.context(ks) as tctx:
        tctx.master.addons.add(d)
        ks.running()
        assert ks.keepgoing()

        d.val = False
        assert not ks.keepgoing()
        await asyncio.sleep(0.3)
        assert ks.is_shutdown
