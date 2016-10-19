import contextlib

from . import tutils
import netlib.tutils

from mitmproxy import master
from mitmproxy import io
from mitmproxy import proxy
from mitmproxy import http
from mitmproxy import options


class TestMaster:
    pass


class MasterTest:

    def cycle(self, master, content):
        f = tutils.tflow(req=netlib.tutils.treq(content=content))
        master.clientconnect(f.client_conn)
        master.serverconnect(f.server_conn)
        master.request(f)
        if not f.error:
            f.response = http.HTTPResponse.wrap(
                netlib.tutils.tresp(content=content)
            )
            master.response(f)
        master.clientdisconnect(f)
        return f

    def dummy_cycle(self, master, n, content):
        for i in range(n):
            self.cycle(master, content)
        master.shutdown()

    def flowfile(self, path):
        f = open(path, "wb")
        fw = io.FlowWriter(f)
        t = tutils.tflow(resp=True)
        fw.add(t)
        f.close()


class RecordingMaster(master.Master):
    def __init__(self, *args, **kwargs):
        master.Master.__init__(self, *args, **kwargs)
        self.event_log = []

    def add_log(self, e, level):
        self.event_log.append((level, e))


@contextlib.contextmanager
def mockctx():
    o = options.Options(refresh_server_playback = True, keepserving=False)
    m = RecordingMaster(o, proxy.DummyServer(o))
    with m.handlecontext():
        yield
