from unittest import mock

from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import io
from mitmproxy.proxy import server_hooks
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class MasterTest:

    async def cycle(self, master, content):
        f = tflow.tflow(req=tutils.treq(content=content))
        layer = mock.Mock("mitmproxy.proxy.protocol.base.Layer")
        layer.client_conn = f.client_conn
        layer.reply = controller.DummyReply()
        await master.addons.handle_lifecycle(server_hooks.ClientConnectedHook(layer))
        for e in eventsequence.iterate(f):
            await master.addons.handle_lifecycle(e)
        await master.addons.handle_lifecycle(server_hooks.ClientDisconnectedHook(layer))
        return f

    async def dummy_cycle(self, master, n, content):
        for i in range(n):
            await self.cycle(master, content)
        await master._shutdown()

    def flowfile(self, path):
        with open(path, "wb") as f:
            fw = io.FlowWriter(f)
            t = tflow.tflow(resp=True)
            fw.add(t)
