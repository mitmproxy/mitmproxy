import sys
import time
from functools import wraps
from functools import partial

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.io import tnetstring
from mitmproxy.addons.serialization import protobuf
from mitmproxy.addons.serialization import dummysession


def watcher(func):
    """
    Decorator for dumpers.
    Shows how much time it
    takes to create the blog,
    together with its size.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        ctx.log(f"{func.__name__} took {end-start} seconds")
        return result
    return wrapper


class DumpWatcher:

    """
        A simple test to measure how different serialization
        modules behave in dumping and loading flows.
    """

    default_tpath = "./tmp/dumps-tnet"

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
        if ctx.options.store_dumps:
            self.serializers['mitmproxy.io.tnetstring'] = watcher(
                partial(tnetstring.dump, file_handle=self.default_tpath))
            self.serializers['mitmproxy.addons.serialization.protobuf'] = watcher(
                partial(protobuf.dump, session=self.session))

            self.deserializers['mitmproxy.io.tnetstring'] = watcher(tnetstring.load)
            self.deserializers['mitmproxy.addons.serialization.protobuf'] = watcher(protobuf.load)
        else:
            for s in self.s_modules:
                m = sys.modules[s]
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

    def _run_loads(self):
        if self.rets:
            for d in self.deserializers:
                ctx.log(f"{d} module: ")
                self.deserializers[d](self.rets[d])

    def _run_loads_file(self):
        ctx.log('mitmproxy.io.tnetstring module: ')
        self.deserializers['mitmproxy.io.tnetstring'](
            self.default_tpath)
        ctx.log('mitmproxy.addons.serialization.protobuf module: ')
        self.deserializers['mitmproxy.addons.serialization.protobuf'](
            self.session, self.rets['mitmproxy.addons.serialization.protobuf'])

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
                self._run_dumps()
                ctx.log("<LOADS>")
                self._run_loads()
            ctx.log("[/==DumpWatcher==]")


addons = [
    DumpWatcher()
]
