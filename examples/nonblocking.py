import time
from mitmproxy.script import concurrent


@concurrent  # Remove this and see what happens
def request(context, flow):
    context.log("handle request: %s%s" % (flow.request.host, flow.request.path))
    time.sleep(5)
    context.log("start  request: %s%s" % (flow.request.host, flow.request.path))
