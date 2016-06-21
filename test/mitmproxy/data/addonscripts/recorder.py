from mitmproxy import controller
from mitmproxy import ctx

call_log = []

# Keep a log of all possible event calls
evts = list(controller.Events) + ["configure"]
for i in evts:
    def mkprox():
        evt = i

        def prox(*args, **kwargs):
            lg = (evt, args, kwargs)
            if evt != "log":
                ctx.log.info(str(lg))
            call_log.append(lg)
        return prox
    globals()[i] = mkprox()
