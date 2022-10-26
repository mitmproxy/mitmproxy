import asyncio
import logging
import traceback
from typing import Optional

from mitmproxy import addonmanager, hooks
from mitmproxy import command
from mitmproxy import eventsequence
from mitmproxy import http
from mitmproxy import log
from mitmproxy import options
from . import ctx as mitmproxy_ctx
from .proxy.mode_specs import ReverseMode

logger = logging.getLogger(__name__)


class Master:
    """
    The master handles mitmproxy's main event loop.
    """

    event_loop: asyncio.AbstractEventLoop

    def __init__(self, opts, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.options: options.Options = opts or options.Options()
        self.commands = command.CommandManager(self)
        self.addons = addonmanager.AddonManager(self)

        self.log = log.Log(self)  # deprecated, do not use.
        self._legacy_log_events = log.LegacyLogEvents(self)
        self._legacy_log_events.install()

        # We expect an active event loop here already because some addons
        # may want to spawn tasks during the initial configuration phase,
        # which happens before run().
        self.event_loop = event_loop or asyncio.get_running_loop()
        try:
            self.should_exit = asyncio.Event()
        except RuntimeError:  # python 3.9 and below
            self.should_exit = asyncio.Event(loop=self.event_loop)  # type: ignore
        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = self.log  # deprecated, do not use.
        mitmproxy_ctx.options = self.options

    async def run(self) -> None:
        old_handler = self.event_loop.get_exception_handler()
        self.event_loop.set_exception_handler(self._asyncio_exception_handler)
        try:
            self.should_exit.clear()

            if ec := self.addons.get("errorcheck"):
                await ec.shutdown_if_errored()
            if ps := self.addons.get("proxyserver"):
                await ps.setup_servers()
            if ec := self.addons.get("errorcheck"):
                await ec.shutdown_if_errored()
                ec.finish()
            await self.running()
            try:
                await self.should_exit.wait()
            finally:
                # .wait might be cancelled (e.g. by sys.exit)
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
        self._legacy_log_events.uninstall()

    def _asyncio_exception_handler(self, loop, context):
        try:
            exc: Exception = context["exception"]
        except KeyError:
            logger.error(
                f"Unhandled asyncio error: {context}"
                "\nPlease lodge a bug report at:"
                + "\n\thttps://github.com/mitmproxy/mitmproxy/issues"
            )
        else:
            if isinstance(exc, OSError) and exc.errno == 10038:
                return  # suppress https://bugs.python.org/issue43253
            logger.error(
                "\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                + "\nPlease lodge a bug report at:"
                + "\n\thttps://github.com/mitmproxy/mitmproxy/issues"
            )

    async def load_flow(self, f):
        """
        Loads a flow
        """

        if isinstance(f, http.HTTPFlow) and len(self.options.mode) == 1 and self.options.mode[0].startswith("reverse:"):
            # When we load flows in reverse proxy mode, we adjust the target host to
            # the reverse proxy destination for all flows we load. This makes it very
            # easy to replay saved flows against a different host.
            # We may change this in the future so that clientplayback always replays to the first mode.
            mode = ReverseMode.parse(self.options.mode[0])
            f.request.host, f.request.port, *_ = mode.address
            f.request.scheme = mode.scheme

        for e in eventsequence.iterate(f):
            await self.addons.handle_lifecycle(e)
