import asyncio
import warnings
from typing import Optional

from mitmproxy import controller, ctx, flow, log, master, options, platform
from mitmproxy.flow import Error
from mitmproxy.proxy import commands
from mitmproxy.proxy import server
from mitmproxy.utils import asyncio_utils, human


class AsyncReply(controller.Reply):
    """
    controller.Reply.q.get() is blocking, which we definitely want to avoid in a coroutine.
    This stub adds a .done asyncio.Event() that can be used instead.
    """

    def __init__(self, *args):
        self.done = asyncio.Event()
        self.loop = asyncio.get_event_loop()
        super().__init__(*args)

    def commit(self):
        super().commit()
        try:
            self.loop.call_soon_threadsafe(lambda: self.done.set())
        except RuntimeError:  # pragma: no cover
            pass  # event loop may already be closed.

    def kill(self, force=False):  # pragma: no cover
        warnings.warn("reply.kill() is deprecated, set the error attribute instead.", DeprecationWarning, stacklevel=2)
        self.obj.error = flow.Error(Error.KILLED_MESSAGE)


class ProxyConnectionHandler(server.StreamConnectionHandler):
    master: master.Master

    def __init__(self, master, r, w, options):
        self.master = master
        super().__init__(r, w, options)
        self.log_prefix = f"{human.format_address(self.client.peername)}: "

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # We currently only support single-argument hooks.
            data, = hook.args()
            data.reply = AsyncReply(data)
            await self.master.addons.handle_lifecycle(hook)
            await data.reply.done.wait()
            data.reply = None

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        x.reply = controller.DummyReply()  # type: ignore
        asyncio_utils.create_task(
            self.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="ProxyConnectionHandler.log"
        )


class Proxyserver:
    """
    This addon runs the actual proxy server.
    """
    server: Optional[asyncio.AbstractServer]
    listen_port: int
    master: master.Master
    options: options.Options
    is_running: bool

    def __init__(self):
        self._lock = asyncio.Lock()
        self.server = None
        self.is_running = False

    def load(self, loader):
        loader.add_option(
            "connection_strategy", str, "lazy",
            "Determine when server connections should be established.",
            choices=("eager", "lazy")
        )
        loader.add_option(
            "proxy_debug", bool, False,
            "Enable debug logs in the proxy core.",
        )

    def running(self):
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        self.configure(["listen_port"])

    def configure(self, updated):
        if not self.is_running:
            return
        if "mode" in updated and ctx.options.mode == "transparent":  # pragma: no cover
            platform.init_transparent_mode()
        if any(x in updated for x in ["server", "listen_host", "listen_port"]):
            asyncio.create_task(self.refresh_server())

    async def refresh_server(self):
        async with self._lock:
            if self.server:
                await self.shutdown_server()
                self.server = None
            if ctx.options.server:
                if not ctx.master.addons.get("nextlayer"):
                    ctx.log.warn("Warning: Running proxyserver without nextlayer addon!")
                self.server = await asyncio.start_server(
                    self.handle_connection,
                    self.options.listen_host,
                    self.options.listen_port,
                )
                addrs = {f"http://{human.format_address(s.getsockname())}" for s in self.server.sockets}
                ctx.log.info(f"Proxy server listening at {' and '.join(addrs)}")

    async def shutdown_server(self):
        ctx.log.info("Stopping server...")
        self.server.close()
        await self.server.wait_closed()
        self.server = None

    async def handle_connection(self, r, w):
        asyncio_utils.set_task_debug_info(
            asyncio.current_task(),
            name=f"Proxyserver.handle_connection",
            client=w.get_extra_info('peername'),
        )
        handler = ProxyConnectionHandler(
            self.master,
            r,
            w,
            self.options
        )
        await handler.handle_client()
