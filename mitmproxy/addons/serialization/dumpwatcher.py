from mitmproxy import ctx
from mitmproxy.io import tnetstring
from mitmproxy.addons.serialization import protobuf
from mitmproxy import http
from functools import wraps
import sys
import time


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
        if func.__name__ == 'dumps':
            ctx.log('{} took {} seconds - {} bytes'.format(func.__name__, end-start, len(result)))
        else:
            ctx.log('{} took {} seconds'.format(func.__name__, end-start))
        return result
    return wrapper


class DumpWatcher:

    """
        A simple test to measure how different serialization
        modules behave in dumping and loading flows.
    """

    def __init__(self):
        self.s_modules = ['mitmproxy.io.tnetstring',
                          'mitmproxy.addons.serialization.protobuf']
        self.serializers = {}
        self.deserializers = {}
        self.blobs = {}
        self.f = None

    def _init_serializers(self):
        """
        Apply watcher decorator
        to dumps/loads methods.
        """
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
                self.blobs[s] = self.serializers[s](self.f.get_state())

    def _run_loads(self):
        if self.blobs:
            for d in self.deserializers:
                ctx.log('{} module: '.format(d))
                self.deserializers[d](self.blobs[d])


    def load(self, loader):
        loader.add_option(
            "dumpwatcher", bool, False,
            """
            Dump every HTTPFlow to event log,
            measuring time and size of blob.
            """
        )

    def running(self):
        self._init_serializers()

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
