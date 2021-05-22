import time
import sys
from mitmproxy.script import concurrent


@concurrent
def request(flow):
    time.sleep(0.1)
