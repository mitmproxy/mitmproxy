import asyncio
import time
import os
from statistics import mean

from mitmproxy import ctx
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
        self.session = dummysession.DummySession()
        self.streaming = False
        self.enabled = False
        self.flow = None
        self.hot_blobs = []
        self.results = []
        self.dump_file = data.pkg_data.path("addons/serialization") + "/tmpdump"
        self._fflushes = 0
        self._stream_period = 0.001
        self._flush_period = 3.0
        self._flush_rate = 150

    def load(self, loader):
        loader.add_option(
            "streamtester", bool, False,
            """
            Generates and dump flows from file,
            measuring dump throughput.
            """
        )

    def running(self):
        if not self.streaming and ctx.options.streamtester:
            ctx.log("<== StreamTester Enabled ==>")
            self.streaming = True
            if os.path.isfile(self.dump_file):
                with open(self.dump_file, 'rb') as handle:
                    ctx.log(f"{os.path.getsize(self.dump_file)/1024} KB file length")
                    self.flow = list(io.FlowReader(handle).stream())[0]
                self.loop.create_task(asyncio.gather(self.writer(), self.stream(), self.stats()))
            else:
                ctx.log(f"[!] Please create a flow dump as {self.dump_file}")

    async def stream(self):
        while True:
            await self.queue.put(protobuf.dumps(self.flow.get_state()))
            await asyncio.sleep(self._stream_period)

    async def writer(self):
        while True:
            await asyncio.sleep(self._flush_period)
            count = 1
            b = await self.queue.get()
            self.hot_blobs.append(b)
            while not self.queue.empty() and count < self._flush_rate:
                try:
                    self.hot_blobs.append(self.queue.get_nowait())
                    count += 1
                except asyncio.QueueEmpty:
                    pass
            start = time.perf_counter()
            n = self._fflush()
            end = time.perf_counter()
            ctx.log(f"dumps/time ratio: {n} / {end-start} -> {n/(end-start)}")
            self.results.append(n / (end - start))
            self._fflushes += 1

    async def stats(self):
        while True:
            await asyncio.sleep(1.0)
            if self._fflushes and not (self._fflushes % 10):
                ctx.log(f"AVG: {mean(self.results)}")

    def _fflush(self):
        self.session.store_many(self.hot_blobs)
        n = len(self.hot_blobs)
        self.hot_blobs = []
        return n


addons = [
    StreamTester()
]


