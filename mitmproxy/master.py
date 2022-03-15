import asyncio
import traceback
from typing import Optional

from mitmproxy import addonmanager, hooks
from mitmproxy import command
from mitmproxy import eventsequence
from mitmproxy import http
from mitmproxy import log
from mitmproxy import options
from mitmproxy.net import server_spec
from . import ctx as mitmproxy_ctx


class Master:
    """
        The master handles mitmproxy's main event loop.
    """

    event_loop: asyncio.AbstractEventLoop

    def __init__(self, opts, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.options: options.Options = opts or options.Options()
        self.commands = command.CommandManager(self)
        self.addons = addonmanager.AddonManager(self)
        self.log = log.Log(self)

        # We expect an active event loop here already because some addons
        # may want to spawn tasks during the initial configuration phase,
        # which happens before run().
        self.event_loop = event_loop or asyncio.get_running_loop()
        try:
            self.should_exit = asyncio.Event()
        except RuntimeError:
            self.should_exit = asyncio.Event(loop=self.event_loop)
        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = self.log
        mitmproxy_ctx.options = self.options

    async def run(self) -> None:
        old_handler = self.event_loop.get_exception_handler()
        self.event_loop.set_exception_handler(self._asyncio_exception_handler)
        try:
            self.should_exit.clear()

            # Handle scheduled tasks (configure()) first.
            await asyncio.sleep(0)
            await self.running()
            await self.should_exit.wait()

            await self.done()
        finally:
            self.event_loop.set_exception_handler(old_handler)

    def shutdown(self):
        """
        Shut down the proxy. This method is thread-safe.
        """
        # We may add an exception argument here.
        self.event_loop.call_soon_threadsafe(self.should_exit.set)

    async def running(self) -> None:
        await self.addons.trigger_event(hooks.RunningHook())

    async def done(self) -> None:
        await self.addons.trigger_event(hooks.DoneHook())

    def _asyncio_exception_handler(self, loop, context):
        exc: Exception = context["exception"]
        if isinstance(exc, OSError) and exc.errno == 10038:
            return  # suppress https://bugs.python.org/issue43253
        self.log.error(
            "\n".join(traceback.format_exception(
                type(exc),
                exc,
                exc.__traceback__
            )) +
            "\nPlease lodge a bug report at:" +
            "\n\thttps://github.com/mitmproxy/mitmproxy/issues"
        )

    async def load_flow(self, f):
        """
        Loads a flow
        """

        if isinstance(f, http.HTTPFlow):
            if self.options.mode.startswith("reverse:"):
                # When we load flows in reverse proxy mode, we adjust the target host to
                # the reverse proxy destination for all flows we load. This makes it very
                # easy to replay saved flows against a different host.
                _, upstream_spec = server_spec.parse_with_mode(self.options.mode)
                f.request.host, f.request.port = upstream_spec.address
                f.request.scheme = upstream_spec.scheme

        for e in eventsequence.iterate(f):
            await self.addons.handle_lifecycle(e)
