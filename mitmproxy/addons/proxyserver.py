import asyncio
import warnings
from typing import Optional

from mitmproxy import controller, ctx, eventsequence, log, master, options
from mitmproxy.flow import Error
from mitmproxy.proxy2 import commands
from mitmproxy.proxy2 import server
from mitmproxy.utils import human


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
        self.loop.call_soon_threadsafe(lambda: self.done.set())

    def kill(self, force=False):
        warnings.warn("reply.kill() is deprecated, set the error attribute instead.", PendingDeprecationWarning)
        self.obj.error = Error.KILLED_MESSAGE


class ProxyConnectionHandler(server.ConnectionHandler):
    master: master.Master

    def __init__(self, master, r, w, options):
        self.master = master
        super().__init__(r, w, options)
        self.log_prefix = f"{human.format_address(self.client.address)}: "

    async def handle_hook(self, hook: commands.Hook) -> None:
        with self.timeout_watchdog.disarm():
            # TODO: We currently only support single-argument hooks.
            data, = hook.as_tuple()
            data.reply = AsyncReply(data)
            await self.master.addons.handle_lifecycle(hook.name, data)
            await data.reply.done.wait()

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        x.reply = controller.DummyReply()
        asyncio.ensure_future(
            self.master.addons.handle_lifecycle("log", x)
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
        # Hack: Update allowed events to include new ones.
        eventsequence.Events = frozenset(
            eventsequence.Events | set(commands.all_hooks.keys())
        )

    def running(self):
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        self.configure(["listen_port"])

    def configure(self, updated):
        if not self.is_running:
            return
        if any(x in updated for x in ["listen_host", "listen_port"]):
            asyncio.ensure_future(self.start_server())

    async def start_server(self):
        async with self._lock:
            if self.server:
                await self.shutdown_server()
            print("Starting server...")
            self.server = await asyncio.start_server(
                self.handle_connection,
                self.options.listen_host,
                self.options.listen_port + 1,
            )

    async def shutdown_server(self):
        print("Stopping server...")
        self.server.close()
        await self.server.wait_closed()
        self.server = None

    async def handle_connection(self, r, w):
        handler = ProxyConnectionHandler(
            self.master,
            r,
            w,
            self.options
        )
        await handler.handle_client()
