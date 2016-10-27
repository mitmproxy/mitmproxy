import time

from mitmproxy.script import concurrent


@concurrent  # Remove this and see what happens
def request(flow):
    # You don't want to use mitmproxy.ctx from a different thread
    print("handle request: %s%s" % (flow.request.host, flow.request.path))
    time.sleep(5)
    print("start  request: %s%s" % (flow.request.host, flow.request.path))
