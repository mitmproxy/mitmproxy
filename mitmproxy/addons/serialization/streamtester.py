import os
import asyncio
import random
import time

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy.io import io
from mitmproxy.utils import data
from mitmproxy.addons.serialization import protobuf, dummysession


class StreamTester:

    """
    Generates a constant stream of flows and
    measure protobuf dumping throughput.
    """

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.flow = None
        self.streaming = False
        self.enabled = False
        self.session = dummysession.DummySession()
        self.hot_flows = []
        self.dump_file = data.pkg_data.path("addons/serialization") + "/tmpdump"

    def load(self, loader):
        loader.add_option(
            "streamtester", bool, False,
            """
            Generates and dump flows from file,
            measuring dump throughput.
            """
        )

    def configure(self, updates):
        if "streamtester" in updates:
            self.enabled = True

    def running(self):
        ctx.log(f"Path is running? ===> {self.loop.is_running()}")
        if not self.streaming and self.enabled:
            self.streaming = True
            with open(self.dump_file, 'rb') as handle:
                self.flow = list(io.FlowReader(handle).stream())[0]
            self.loop.create_task(asyncio.gather(self.writer(), self.stream()))

    async def stream(self):
        # producing a constant stream
        while True:
            await self.queue.put(self.flow)
            await asyncio.sleep(0.0001)

    async def writer(self):
        while True:
            count = 1
            f = await self.queue.get()
            self.hot_flows.append(f)
            while not self.queue.empty() and count < 150:
                try:
                    self.hot_flows.append(self.queue.get_nowait())
                    count += 1
                except asyncio.QueueEmpty:
                    pass
            self._flush()

    def _flush(self):
        blobs = []
        while self.hot_flows:
            f = self.hot_flows.pop()
            blobs.append(protobuf.dumps(f.get_state()))
        self.session.store_many(blobs)
        ctx.log(f"Flushed {len(blobs)} flows")


addons = [
    StreamTester()
]


