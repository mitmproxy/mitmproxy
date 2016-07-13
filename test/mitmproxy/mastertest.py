import mock

from . import tutils
import netlib.tutils

from mitmproxy import flow, proxy, models, controller


class MasterTest:
    def invoke(self, master, handler, message):
        with master.handlecontext():
            func = getattr(master, handler)
            func(message)
        message.reply = controller.DummyReply()

    def cycle(self, master, content):
        f = tutils.tflow(req=netlib.tutils.treq(content=content))
        l = proxy.Log("connect")
        l.reply = mock.MagicMock()
        master.log(l)
        master.clientconnect(f.client_conn)
        master.serverconnect(f.server_conn)
        master.request(f)
        if not f.error:
            f.response = models.HTTPResponse.wrap(netlib.tutils.tresp(content=content))
            f.reply.acked = False
            f = master.response(f)
        f.client_conn.reply.acked = False
        master.clientdisconnect(f.client_conn)
        return f

    def dummy_cycle(self, master, n, content):
        for i in range(n):
            self.cycle(master, content)
        master.shutdown()

    def flowfile(self, path):
        f = open(path, "wb")
        fw = flow.FlowWriter(f)
        t = tutils.tflow(resp=True)
        fw.add(t)
        f.close()
