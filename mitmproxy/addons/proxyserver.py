import asyncio
import queue
import threading

from mitmproxy import ctx, controller, log
from mitmproxy.proxy.protocol2 import commands
from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.server import server_async


class AsyncReply(controller.Reply):
    # temporary glue code - let's see how many years it survives.
    def __init__(self, submit, *args):
        self.submit = submit
        super().__init__(*args)

    def commit(self):
        super().commit()
        self.submit(self.q.get_nowait())


class ProxyConnectionHandler(server_async.ConnectionHandler):
    event_queue: queue.Queue
    loop: asyncio.AbstractEventLoop

    def __init__(self, event_queue, loop, r, w):
        self.event_queue = event_queue
        self.loop = loop
        super().__init__(r, w)

    async def handle_hook(self, hook: commands.Hook) -> None:
        q = asyncio.Queue()
        submit = lambda x: self.loop.call_soon_threadsafe(lambda: q.put_nowait(x))
        hook.data.reply = AsyncReply(submit, hook.data)
        self.event_queue.put((hook.name, hook.data))
        reply = await q.get()
        self.server_event(events.HookReply(hook, reply))

    def _debug(self, *args):
        x = log.LogEntry(" ".join(str(x) for x in args), "warn")
        x.reply = controller.DummyReply()
        self.event_queue.put(("log",  x))

class Proxyserver:
    """
    This addon runs the actual proxy server.
    """

    def __init__(self):
        self.server = None
        self.loop = asyncio.get_event_loop()
        self.listen_port = None
        self.event_queue = None
        self._lock = asyncio.Lock()

    def running(self):
        self.event_queue = ctx.master.event_queue
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    async def start(self):
        async with self._lock:
            if self.server:
                print("Stopping server...")
                self.server.close()
                await self.server.wait_closed()

            print("Starting server...")
            self.server = await asyncio.start_server(
                self.handle_connection,
                '127.0.0.1',
                self.listen_port,
                loop=self.loop
            )

    async def handle_connection(self, r, w):
        await ProxyConnectionHandler(self.event_queue, self.loop, r, w).handle_client()

    def configure(self, updated):
        if "listen_port" in updated:
            self.listen_port = ctx.options.listen_port + 1

            # not sure if this actually required...
            self.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(self.start()))

    def request(self, flow):
        pass
        # test live options changes.
        # print("Changing port...")
        # ctx.options.listen_port += 1
