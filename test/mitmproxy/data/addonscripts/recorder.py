from mitmproxy import controller
from mitmproxy import ctx
import sys

call_log = []

if len(sys.argv) > 1:
    name = sys.argv[1]
else:
    name = "solo"

# Keep a log of all possible event calls
evts = list(controller.Events) + ["configure"]
for i in evts:
    def mkprox():
        evt = i

        def prox(*args, **kwargs):
            lg = (name, evt, args, kwargs)
            if evt != "log":
                ctx.log.info(str(lg))
            call_log.append(lg)
            ctx.log.debug("%s %s" % (name, evt))
        return prox
    globals()[i] = mkprox()
