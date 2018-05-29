import asyncio
import time
import os

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
        loader.add_option(
            "stream_period", float, 0.03,
            """
            Set time interval between consequent
            flow streams.
            """
        )
        loader.add_option(
            "flush_period", float, 3.0,
            """
            Set time interval for flush routine.
            """
        )
        loader.add_option(
            "flush_rate", int, 150,
            """
            Set maximum number of flushes to disk,
            per flush routine.
            """
        )

    def configure(self, updates):
        if ctx.options.streamtester:
            ctx.log("===> Stream Throughput test enabled. ")
            self.enabled = True
            for opt in ['stream_period', 'flush_rate', 'flush_period']:
                if opt in updates:
                    ctx.log(f"{opt} set to {updates[opt]}")

    def running(self):
        if not self.streaming and self.enabled:
            self.streaming = True
            if os.path.isfile(self.dump_file):
                with open(self.dump_file, 'rb') as handle:
                    ctx.log(f"With {os.path.getsize(self.dump_file)/1024} KB file length: ")
                    self.flow = list(io.FlowReader(handle).stream())[0]
                self.loop.create_task(asyncio.gather(self.writer(), self.stream()))
            else:
                ctx.log(f"[!] Please create a flow dump as {self.dump_file}")

    async def stream(self):
        while True:
            await self.queue.put(self.flow)
            await asyncio.sleep(ctx.options.stream_period)

    async def writer(self):
        while True:
            await asyncio.sleep(ctx.options.flush_period)
            count = 1
            f = await self.queue.get()
            self.hot_flows.append(f)
            while not self.queue.empty() and count < ctx.options.flush_rate:
                try:
                    self.hot_flows.append(self.queue.get_nowait())
                    count += 1
                except asyncio.QueueEmpty:
                    pass
            start = time.perf_counter()
            n = self._fflush()
            end = time.perf_counter()
            tput = n / (end - start)
            ctx.log(f"Flushing at {tput} f/s")

    def _fflush(self):
        blobs = []
        while self.hot_flows:
            f = self.hot_flows.pop()
            blobs.append(protobuf.dumps(f.get_state()))
        self.session.store_many(blobs)
        return len(blobs)


addons = [
    StreamTester()
]


