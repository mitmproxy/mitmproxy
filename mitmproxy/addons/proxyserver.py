import asyncio

from mitmproxy import ctx, controller, log, options, master
from mitmproxy.proxy2 import commands
from mitmproxy.proxy2 import events
from mitmproxy.proxy2 import server


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


class ProxyConnectionHandler(server.ConnectionHandler):
    master: master.Master

    def __init__(self, master, r, w, options):
        self.master = master
        super().__init__(r, w, options)

    async def handle_hook(self, hook: commands.Hook) -> None:
        hook.data.reply = AsyncReply(hook.data)
        await self.master.addons.handle_lifecycle(hook.name, hook.data)
        await hook.data.reply.done.wait()
        if hook.blocking:
            self.server_event(events.HookReply(hook))

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(message, level)
        x.reply = controller.DummyReply()
        asyncio.ensure_future(
            self.master.addons.handle_lifecycle("log", x)
        )


class Proxyserver:
    """
    This addon runs the actual proxy server.
    """
    server: asyncio.AbstractServer
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
            "connection_strategy", str, "eager",
            "Determine when server connections should be established.",
            choices=("eager", "lazy")
        )

    def running(self):
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        self.configure(["listen_port"])

    def configure(self, updated):
        if not self.is_running:
            return
        if "listen_port" in updated:
            self.listen_port = ctx.options.listen_port + 1
            asyncio.ensure_future(self.start_server())

    async def start_server(self):
        async with self._lock:
            if self.server:
                await self.shutdown_server()
            print("Starting server...")
            self.server = await asyncio.start_server(
                self.handle_connection,
                '127.0.0.1',
                self.listen_port,
            )

    async def shutdown_server(self):
        print("Stopping server...")
        self.server.close()
        await self.server.wait_closed()
        self.server = None

    async def handle_connection(self, r, w):
        await ProxyConnectionHandler(
            self.master,
            r,
            w,
            self.options
        ).handle_client()
