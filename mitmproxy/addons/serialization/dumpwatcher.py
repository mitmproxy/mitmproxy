import sys
import time
from functools import wraps

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.io import tnetstring
from mitmproxy.utils import data
from mitmproxy.addons.serialization import protobuf
from mitmproxy.addons.serialization import dummysession


def watcher(func):
    """
    Decorator for dumpers.
    Shows how much time it
    takes to create/retrieve
    the blob.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        ctx.log(f" ===> took {end-start} seconds")
        return result
    return wrapper


class DumpWatcher:

    """
        A simple test to measure how different serialization
        modules behave in dumping and loading flows.
    """

    default_tpath = data.pkg_data.path('addons/serialization/') + '/dumps-tnet'

    def __init__(self):
        self.s_modules = ['mitmproxy.io.tnetstring',
                          'mitmproxy.addons.serialization.protobuf']
        self.serializers = {}
        self.deserializers = {}
        self.rets = {}
        self.f = None
        self.session = dummysession.DummySession()

    def _init_dumpers(self):
        """
        Apply watcher decorator
        to dumps/loads methods.
        """
        for s in self.s_modules:
            m = sys.modules[s]
            if ctx.options.store_dumps:
                self.serializers[s] = watcher(m.dump)
                self.deserializers[s] = watcher(m.load)
            else:
                self.serializers[s] = watcher(m.dumps)
                self.deserializers[s] = watcher(m.loads)

    def _run_dumps(self):
        """
        Dump flow and collect
        performance informations.
        """
        if self.f:
            for s in self.serializers:
                ctx.log('{} module: '.format(s))
                self.rets[s] = self.serializers[s](self.f.get_state())

    def _run_dumps_file(self):
        if self.f:
            for s in self.serializers:
                ctx.log(f'{s} module: ')
                if s == 'mitmproxy.io.tnetstring':
                    with open(self.default_tpath, "wb") as storage_write:
                        self.rets[s] = self.serializers[s](self.f.get_state(), storage_write)
                elif s == 'mitmproxy.addons.serialization.protobuf':
                    self.rets[s] = self.serializers[s](self.f.get_state(), self.session)

    def _run_loads(self):
        if self.rets:
            for d in self.deserializers:
                ctx.log(f"{d} module: ")
                self.deserializers[d](self.rets[d])

    def _run_loads_file(self):
        for d in self.deserializers:
            ctx.log(f'{d} module: ')
            if d == 'mitmproxy.io.tnetstring':
                with open(self.default_tpath, "rb") as storage_read:
                    self.deserializers[d](
                        storage_read)
            elif d == 'mitmproxy.addons.serialization.protobuf':
                self.deserializers[d](
                    self.session, self.rets[d])

    def load(self, loader):
        loader.add_option(
            "dumpwatcher", bool, False,
            """
            Dump every HTTPFlow response to event log,
            measuring time and size of blob.
            """
        )
        loader.add_option(
            "store_dumps", bool, False,
            """
            Store flow dumps into file or DB
            (depending on module) to further
            measure performances.
            """
        )

    def running(self):
        self._init_dumpers()

    def response(self, flow):
        """
        Send flow state to
        dump/load sequence.
        """
        if ctx.options.dumpwatcher:
            ctx.log("[==DumpWatcher==]")
            if isinstance(flow, http.HTTPFlow):
                self.f = flow
                ctx.log("<DUMPS>")
                if ctx.options.store_dumps:
                    self._run_dumps_file()
                else:
                    self._run_dumps()
                ctx.log("<LOADS>")
                if ctx.options.store_dumps:
                    self._run_loads_file()
                else:
                    self._run_loads()
            ctx.log("[/==DumpWatcher==]")

    def done(self):
        self.session.close()


addons = [
    DumpWatcher()
]
