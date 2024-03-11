import asyncio
import cProfile
import logging

from mitmproxy import ctx


class Benchmark:
    """
    A simple profiler addon.
    """

    def __init__(self):
        self.pr = cProfile.Profile()
        self.started = False

        self.resps = 0
        self.reqs = 0

    def request(self, f):
        self.reqs += 1

    def response(self, f):
        self.resps += 1

    async def procs(self):
        logging.error("starting benchmark")
        backend = await asyncio.create_subprocess_exec("devd", "-q", "-p", "10001", ".")
        traf = await asyncio.create_subprocess_exec(
            "wrk",
            "-c50",
            "-d5s",
            "http://localhost:%s/benchmark.py" % ctx.master.server.address[1],
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await traf.communicate()
        with open(ctx.options.benchmark_save_path + ".bench", mode="wb") as f:
            f.write(stdout)
        logging.error(f"Proxy saw {self.reqs} requests, {self.resps} responses")
        logging.error(stdout.decode("ascii"))
        backend.kill()
        ctx.master.shutdown()

    def load(self, loader):
        loader.add_option(
            "benchmark_save_path",
            str,
            "/tmp/profile",
            "Destination for the .prof and .bench result files",
        )
        ctx.options.update(
            mode="reverse:http://devd.io:10001",
        )
        self.pr.enable()

    def running(self):
        if not self.started:
            self.started = True
            self._task = asyncio.create_task(self.procs())

    def done(self):
        self.pr.dump_stats(ctx.options.benchmark_save_path + ".prof")


addons = [Benchmark()]
