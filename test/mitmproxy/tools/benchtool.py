# Profile mitmdump with apachebench and
# yappi (https://code.google.com/p/yappi/)
#
# Requirements:
# - Apache Bench "ab" binary
# - pip install click yappi

from mitmproxy.main import mitmdump
from os import system
from threading import Thread
import time

import yappi
import click


class ApacheBenchThread(Thread):

    def __init__(self, concurrency):
        self.concurrency = concurrency
        super(ApacheBenchThread, self).__init__()

    def run(self):
        time.sleep(2)
        system(
            "ab -n 1024 -c {} -X 127.0.0.1:8080 http://example.com/".format(self.concurrency))


@click.command()
@click.option('--profiler', default="none", type=click.Choice(['none', 'yappi']))
@click.option('--clock-type', default="cpu", type=click.Choice(['wall', 'cpu']))
@click.option('--concurrency', default=1, type=click.INT)
def main(profiler, clock_type, concurrency):

    outfile = "callgrind.mitmdump-{}-c{}".format(clock_type, concurrency)
    a = ApacheBenchThread(concurrency)
    a.start()

    if profiler == "yappi":
        yappi.set_clock_type(clock_type)
        yappi.start(builtins=True)

    print("Start mitmdump...")
    mitmdump(["-k", "-q", "-S", "1024example"])
    print("mitmdump stopped.")

    print("Save profile information...")
    if profiler == "yappi":
        yappi.stop()
        stats = yappi.get_func_stats()
        stats.save(outfile, type='callgrind')
    print("Done.")

if __name__ == '__main__':
    main()
