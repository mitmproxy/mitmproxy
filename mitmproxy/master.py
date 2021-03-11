import asyncio
import logging
import sys
import threading
import traceback

from mitmproxy import addonmanager, hooks
from mitmproxy import command
from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import http
from mitmproxy import log
from mitmproxy import options
from mitmproxy.net import server_spec
from . import ctx as mitmproxy_ctx

# Conclusively preventing cross-thread races on proxy shutdown turns out to be
# very hard. We could build a thread sync infrastructure for this, or we could
# wait until we ditch threads and move all the protocols into the async loop.
# Until then, silence non-critical errors.
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


class Master:
    """
        The master handles mitmproxy's main event loop.
    """

    def __init__(self, opts):
        self.should_exit = threading.Event()
        self.event_loop = asyncio.get_event_loop()
        self.options: options.Options = opts or options.Options()
        self.commands = command.CommandManager(self)
        self.addons = addonmanager.AddonManager(self)
        self._server = None
        self.log = log.Log(self)

        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = self.log
        mitmproxy_ctx.options = self.options

    def start(self):
        self.should_exit.clear()

    async def running(self):
        self.addons.trigger(hooks.RunningHook())

    def run_loop(self, loop):
        self.start()
        asyncio.ensure_future(self.running())

        exc = None
        try:
            loop()
        except Exception:  # pragma: no cover
            exc = traceback.format_exc()
        finally:
            if not self.should_exit.is_set():  # pragma: no cover
                self.shutdown()
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            for p in tasks:
                p.cancel()
            loop.close()

        if exc:  # pragma: no cover
            print(exc, file=sys.stderr)
            print("mitmproxy has crashed!", file=sys.stderr)
            print("Please lodge a bug report at:", file=sys.stderr)
            print("\thttps://github.com/mitmproxy/mitmproxy/issues", file=sys.stderr)

        self.addons.trigger(hooks.DoneHook())

    def run(self):
        loop = asyncio.get_event_loop()
        self.run_loop(loop.run_forever)

    async def _shutdown(self):
        self.should_exit.set()
        loop = asyncio.get_event_loop()
        loop.stop()

    def shutdown(self):
        """
            Shut down the proxy. This method is thread-safe.
        """
        if not self.should_exit.is_set():
            self.should_exit.set()
            ret = asyncio.run_coroutine_threadsafe(self._shutdown(), loop=self.event_loop)
            # Weird band-aid to make sure that self._shutdown() is actually executed,
            # which otherwise hangs the process as the proxy server is threaded.
            # This all needs to be simplified when the proxy server runs on asyncio as well.
            if not self.event_loop.is_running():  # pragma: no cover
                try:
                    self.event_loop.run_until_complete(asyncio.wrap_future(ret))
                except RuntimeError:
                    pass  # Event loop stopped before Future completed.

    def _change_reverse_host(self, f):
        """
        When we load flows in reverse proxy mode, we adjust the target host to
        the reverse proxy destination for all flows we load. This makes it very
        easy to replay saved flows against a different host.
        """
        if self.options.mode.startswith("reverse:"):
            _, upstream_spec = server_spec.parse_with_mode(self.options.mode)
            f.request.host, f.request.port = upstream_spec.address
            f.request.scheme = upstream_spec.scheme

    async def load_flow(self, f):
        """
        Loads a flow
        """

        if isinstance(f, http.HTTPFlow):
            self._change_reverse_host(f)

        f.reply = controller.DummyReply()
        for e in eventsequence.iterate(f):
            await self.addons.handle_lifecycle(e)
