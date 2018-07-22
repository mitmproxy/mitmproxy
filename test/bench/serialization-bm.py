import asyncio
import time
import os
from statistics import mean

from mitmproxy import ctx
from mitmproxy.io import db
from mitmproxy.test import tflow


class StreamTester:

    """
    Generates a constant stream of flows and
    measure protobuf dumping throughput.
    """

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.dbh = None
        self.streaming = False
        self.tf = None
        self.out = None
        self.hot_flows = []
        self.results = []
        self._fflushes = 0
        self._stream_period = 0.001
        self._flush_period = 3.0
        self._flush_rate = 150

    def load(self, loader):
        loader.add_option(
            "testflow_size",
            int,
            1000,
            "Length in bytes of test flow content"
        )
        loader.add_option(
            "benchmark_save_path",
            str,
            "/tmp/stats",
            "Destination for the stats result file"
        )

    def running(self):
        if not self.streaming:
            ctx.log("<== Serialization Benchmark Enabled ==>")
            self.tf = tflow.tflow()
            self.tf.request.content = b'A' * ctx.options.testflow_size
            ctx.log(f"With content size: {len(self.tf.request.content)} B")
            self.dbh = db.DBHandler("/tmp/temp.sqlite", mode='write')
            self.out = open(ctx.options.benchmark_save_path, "w")
            self.streaming = True
            self.loop.create_task(asyncio.gather(self.writer(), self.stream(), self.stats()))

    async def stream(self):
        while True:
            await self.queue.put(self.tf)
            await asyncio.sleep(self._stream_period)

    async def writer(self):
        while True:
            await asyncio.sleep(self._flush_period)
            count = 1
            f = await self.queue.get()
            self.hot_flows.append(f)
            while not self.queue.empty() and count < self._flush_rate:
                try:
                    self.hot_flows.append(self.queue.get_nowait())
                    count += 1
                except asyncio.QueueEmpty:
                    pass
            start = time.perf_counter()
            n = self._fflush()
            end = time.perf_counter()
            self.out.write(f"dumps/time ratio: {n} / {end-start} -> {n/(end-start)}\n")
            self.results.append(n / (end - start))
            self._fflushes += 1
            ctx.log(f"Flushes: {self._fflushes}")

    async def stats(self):
        while True:
            await asyncio.sleep(1.0)
            if self._fflushes == 21:
                self.out.write(f"AVG : {mean(self.results)}\n")
                ctx.log(f"<== Benchmark Ended. Collect results at {ctx.options.benchmark_save_path} ==>")
                self.out.close()
                del self.dbh
                os.remove("/tmp/temp.sqlite")
                ctx.master.shutdown()

    def _fflush(self):
        self.dbh.store(self.hot_flows)
        n = len(self.hot_flows)
        self.hot_flows = []
        return n


addons = [
    StreamTester()
]
