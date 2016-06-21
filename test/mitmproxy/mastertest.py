import mock

from . import tutils
import netlib.tutils

from mitmproxy import proxy
from mitmproxy import models
from mitmproxy import controller
from mitmproxy.builtins import script


class MasterTest:
    def invoke(self, master, handler, message):
        with master.handlecontext(message):
            func = getattr(master, handler)
            func(message)
        message.reply = controller.DummyReply()

    def cycle(self, master, content):
        f = tutils.tflow(req=netlib.tutils.treq(content=content))
        l = proxy.Log("connect")
        l.reply = mock.MagicMock()
        master.log(l)
        self.invoke(master, "clientconnect", f.client_conn)
        self.invoke(master, "clientconnect", f.client_conn)
        self.invoke(master, "serverconnect", f.server_conn)
        self.invoke(master, "request", f)
        if not f.error:
            f.response = models.HTTPResponse.wrap(netlib.tutils.tresp(content=content))
            self.invoke(master, "response", f)
        self.invoke(master, "clientdisconnect", f)
        return f

    def dummy_cycle(self, master, n, content):
        for i in range(n):
            self.cycle(master, content)
        master.shutdown()

    def scriptctx(self, path):
        s = script.Script(path)
        self.master.addons.add(s)
        try:
            yield
        finally:
            self.master.addons.remove(s)
