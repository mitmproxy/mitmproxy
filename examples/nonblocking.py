import time
from libmproxy.script import concurrent

@concurrent
def request(context, flow):
    print "handle request: %s%s" % (flow.request.host, flow.request.path)
    time.sleep(5)
    print "start  request: %s%s" % (flow.request.host, flow.request.path)
