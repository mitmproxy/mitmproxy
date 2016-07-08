import time
import mitmproxy
from mitmproxy.script import concurrent


@concurrent  # Remove this and see what happens
def request(flow):
    mitmproxy.log("handle request: %s%s" % (flow.request.host, flow.request.path))
    time.sleep(5)
    mitmproxy.log("start  request: %s%s" % (flow.request.host, flow.request.path))
