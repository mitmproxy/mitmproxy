import asyncio
import threading

from mitmproxy import ctx
from mitmproxy.proxy.protocol2.server.server_async import ConnectionHandler


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
        await ConnectionHandler(self.event_queue, r, w).handle_client()

    def configure(self, updated):
        if "listen_port" in updated:
            self.listen_port = ctx.options.listen_port + 1

            # not sure if this actually required...
            self.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(self.start()))

    def request(self, flow):
        print("Changing port...")
        ctx.options.listen_port += 1
