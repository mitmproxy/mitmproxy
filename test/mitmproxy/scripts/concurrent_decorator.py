import time
from mitmproxy.script import concurrent

@concurrent
def request(context, flow):
    time.sleep(0.1)
