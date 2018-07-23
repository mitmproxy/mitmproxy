import tempfile
import asyncio
import typing
import time

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
        self.dbh = None
        self.streaming = False
        self.tf = None
        self.out = None
        self.hot_flows = []
        self.results = []
        self._flushes = 0
        self._stream_period = 0.001
        self._flush_period = 3.0
        self._flush_rate = 150
        self._target = 2000
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(maxsize=self._flush_rate * 3, loop=self.loop)
        self.temp = tempfile.NamedTemporaryFile()

    def load(self, loader):
        loader.add_option(
            "testflow_size",
            int,
            1000,
            "Length in bytes of test flow content"
        )
        loader.add_option(
            "benchmark_save_path",
            typing.Optional[str],
            None,
            "Destination for the stats result file"
        )

    def _log(self, msg):
        if self.out:
            self.out.write(msg + '\n')
        else:
            ctx.log(msg)

    def running(self):
        if not self.streaming:
            ctx.log("<== Serialization Benchmark Enabled ==>")
            self.tf = tflow.tflow()
            self.tf.request.content = b'A' * ctx.options.testflow_size
            ctx.log(f"With content size: {len(self.tf.request.content)} B")
            if ctx.options.benchmark_save_path:
                ctx.log(f"Storing results to {ctx.options.benchmark_save_path}")
                self.out = open(ctx.options.benchmark_save_path, "w")
            self.dbh = db.DBHandler(self.temp.name, mode='write')
            self.streaming = True
            tasks = (self.stream, self.writer, self.stats)
            self.loop.create_task(asyncio.gather(*(t() for t in tasks)))

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
            while count < self._flush_rate:
                try:
                    self.hot_flows.append(self.queue.get_nowait())
                    count += 1
                except asyncio.QueueEmpty:
                    pass
            start = time.perf_counter()
            n = self._fflush()
            end = time.perf_counter()
            self._log(f"dumps/time ratio: {n} / {end-start} -> {n/(end-start)}")
            self.results.append(n / (end - start))
            self._flushes += n
            self._log(f"Flows dumped: {self._flushes}")
            ctx.log(f"Progress: {min(100.0, 100.0 * (self._flushes / self._target))}%")

    async def stats(self):
        while True:
            await asyncio.sleep(1.0)
            if self._flushes >= self._target:
                self._log(f"AVG : {mean(self.results)}")
                ctx.log(f"<== Benchmark Ended. Shutting down... ==>")
                if self.out:
                    self.out.close()
                self.temp.close()
                ctx.master.shutdown()

    def _fflush(self):
        self.dbh.store(self.hot_flows)
        n = len(self.hot_flows)
        self.hot_flows = []
        return n


addons = [
    StreamTester()
]
