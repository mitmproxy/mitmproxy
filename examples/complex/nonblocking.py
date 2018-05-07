import time

from mitmproxy.script import concurrent
from mitmproxy import ctx


@concurrent  # Remove this and see what happens
def request(flow):
    # You don't want to use mitmproxy.ctx from a different thread
    ctx.log.info("handle request: %s%s" % (flow.request.host, flow.request.path))
    time.sleep(5)
    ctx.log.info("start  request: %s%s" % (flow.request.host, flow.request.path))
